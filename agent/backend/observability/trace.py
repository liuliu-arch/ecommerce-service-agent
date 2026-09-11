"""公开 Trace 层，统一清洗、结构化和存储 Agent 执行事件。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from course_runtime.course_logging import log_course_event

from api.schemas import *
from config.settings import TRACE_SCHEMA_VERSION

class TraceEventNormalizer:
    """把模块事件整理成公开 trace schema。

    Trace 只记录可展示的执行摘要：工具名、RAG 命中、workflow 状态、HITL 边界、
    Hooks 和成本路径。它不是 hidden CoT，也不保存系统提示词或原始隐私内容。
    """

    _CATEGORY_BY_EVENT = {
        "runtime_context_built": "runtime_context",
        "context_built": "context",
        "route_plan_built": "model",
        "prompt_context_built": "prompt",
        "rag_pre_retrieved": "rag",
        "rag_hybrid_retrieved": "rag",
        "rag_reranked": "rag",
        "tool_started": "tool",
        "tool_finished": "tool",
        "workflow_completed": "workflow",
        "workflow_node_finished": "workflow",
        "human_approval_required": "hitl",
        "hook_executed": "hook",
        "prompt_security_blocked": "prompt",
        "rag_low_confidence_fallback": "rag",
        "degradation_triggered": "degradation",
        "model_route_planned": "model",
        "model_answer_generated": "model",
        "model_answer_skipped": "model",
        "langchain_tool_agent_completed": "tool",
        "tool_clarification_required": "tool",
        "tool_clarification_resolved": "tool",
        "tool_clarification_expired": "tool",
        "received_return_boundary_blocked": "workflow",
        "workflow_resumed": "workflow",
        "human_approval_resolved": "hitl",
        "cost_recorded": "cost",
        "final_answer_generated": "answer",
    }
    _PHONE_PATTERN = re.compile(r"\b1[3-9]\d{9}\b")
    _ADDRESS_PATTERN = re.compile(r"(收货地址|地址)\s*[:：]\s*[^,，。;\n]+")
    _SECRET_PATTERN = re.compile(r"(?i)(api[_ -]?key|access[_ -]?token|secret|sk-[A-Za-z0-9_-]{8,})")

    @classmethod
    def normalize(cls, *, session_id: str, event_type: str, payload: dict[str, Any], step: int) -> TraceEvent:
        """把各模块事件整理成统一公开 Trace，并在写入前做安全清洗。"""
        safe_payload = cls.sanitize(payload)
        category = cls._CATEGORY_BY_EVENT.get(event_type, "system")
        return TraceEvent(
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            agent_mode="ecommerce-agent",
            step=step,
            schema_version=TRACE_SCHEMA_VERSION,
            category=category,
            stage=cls.stage(event_type, safe_payload),
            name=event_type,
            status=cls.status(event_type, safe_payload),
            target=cls.target(event_type, safe_payload),
            ids={
                "session_id": session_id,
                "workflow_id": safe_payload.get("workflow_id"),
                "order_no": safe_payload.get("order_id"),
                "tool_call_id": safe_payload.get("tool_call_id"),
            },
            summary=cls.summary(event_type, safe_payload),
            signals=cls.signals(event_type, safe_payload),
            safety={
                "public_trace": True,
                "hidden_cot_exposed": False,
                "payload_sanitized": safe_payload != payload,
                "contains_sensitive_raw": False,
            },
            payload=safe_payload,
        )

    @classmethod
    def sanitize(cls, value: Any) -> Any:
        """递归清洗 Trace payload，避免系统提示词、隐私和密钥进入公开观察台。"""
        if isinstance(value, dict):
            return {key: cls.sanitize(item) for key, item in value.items() if key not in {"system_prompt", "hidden_reasoning"}}
        if isinstance(value, list):
            return [cls.sanitize(item) for item in value]
        if isinstance(value, str):
            text = cls._PHONE_PATTERN.sub("1**********", value)
            text = cls._ADDRESS_PATTERN.sub(r"\1：[已脱敏地址]", text)
            text = cls._SECRET_PATTERN.sub("[已脱敏密钥]", text)
            text = text.replace("hidden reasoning", "[受保护推理摘要]").replace("隐藏推理", "[受保护推理摘要]")
            return text.replace("系统提示词", "[受保护系统信息]")
        return value

    @staticmethod
    def stage(event_type: str, payload: dict[str, Any]) -> str:
        """从事件类型推断执行阶段，帮助按 Agent 链路阅读 Trace。"""
        if event_type.endswith("_started"):
            return "start"
        if event_type.endswith("_finished") or event_type.endswith("_completed"):
            return "finish"
        if event_type.startswith("rag_"):
            return "retrieval"
        if event_type.startswith("human_approval"):
            return "approval"
        if event_type == "cost_recorded":
            return "cost_summary"
        if event_type == "degradation_triggered":
            return "degradation"
        if event_type == "hook_executed":
            return str(payload.get("hook_type") or "hook")
        return "event"

    @staticmethod
    def status(event_type: str, payload: dict[str, Any]) -> str:
        """把事件转换成稳定状态，便于前端观察台和 Eval 使用。"""
        if payload.get("status"):
            return str(payload["status"])
        if event_type.endswith("_started"):
            return "started"
        if event_type.endswith("_finished") or event_type.endswith("_completed"):
            return "success"
        if event_type == "human_approval_required":
            return "warning"
        return "recorded"

    @staticmethod
    def target(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """抽取事件目标，说明本步处理的是工具、RAG、workflow 还是回答。"""
        return {
            "type": payload.get("target_type") or ("tool" if event_type.startswith("tool_") else None),
            "name": payload.get("tool_name") or payload.get("workflow_type") or payload.get("target_name"),
        }

    @staticmethod
    def summary(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """生成 Trace 摘要，只保留复盘需要的公开信号。"""
        keys = (
            "intent",
            "hit_count",
            "retrieval_stage",
            "tool_name",
            "risk_level",
            "needs_human_approval",
            "pending_action",
            "path_type",
            "tool_call_count",
            "degraded",
            "hook_type",
        )
        return {"event_type": event_type, **{key: payload[key] for key in keys if key in payload}}

    @staticmethod
    def signals(event_type: str, payload: dict[str, Any]) -> list[str]:
        """提取评测可用的公开信号，避免回归测试依赖 hidden reasoning。"""
        signals = [event_type]
        for key in ("tool_name", "workflow_type", "pending_action", "path_type", "hook_type"):
            if payload.get(key):
                signals.append(str(payload[key]))
        if payload.get("needs_human_approval") is True:
            signals.append("needs_human_approval=true")
        return signals


class TraceStore:
    def __init__(self) -> None:
        """初始化本课服务对象，把可替换依赖固定在实例上，便于总演习和测试复用。"""
        self._events: dict[str, list[TraceEvent]] = {}

    def clear(self) -> None:
        """清空测试会话 Trace，保证课程用例之间互不串扰。"""
        self._events.clear()

    def add(self, session_id: str, event_type: str, payload: dict[str, Any]) -> TraceEvent:
        """追加 Trace 事件，并统一补齐 schema、step 和安全摘要。"""
        events = self._events.setdefault(session_id, [])
        event = TraceEventNormalizer.normalize(session_id=session_id, event_type=event_type, payload=payload, step=len(events) + 1)
        events.append(event)
        # Trace 是结构化执行证据；终端 INFO 留给本课各模块自己的教学事件，
        # DEBUG 仍可按发生顺序查看完整的公开 Trace 摘要。
        log_course_event("TRACE_EVENT", event.summary, trace_event=event_type, step=event.step, category=event.category, status=event.status, payload=event.payload)
        return event

    def list(self, session_id: str) -> list[TraceEvent]:
        """按会话读取公开 Trace，供观察台、Eval 和反馈归因共用。"""
        return list(self._events.get(session_id, []))


trace_store = TraceStore()


def record_initial_chat_trace(
    *,
    session_id: str,
    runtime_user_id: str,
    runtime_nickname: str | None,
    runtime_member_level: str | None,
    runtime_risk_level: str | None,
    intent: Intent,
    estimated_tokens: int,
    route_result: Any,
    context_report: dict[str, Any],
    compression_report: dict[str, Any],
) -> None:
    """记录进入主链路时的 Runtime Context、上下文预算和路由结果。"""
    trace_store.add(
        session_id,
        "runtime_context_built",
        {
            "session_id": session_id,
            "runtime_user_id": runtime_user_id,
            "runtime_nickname": runtime_nickname or "unknown",
            "member_level": runtime_member_level or "unknown",
            "risk_level": runtime_risk_level or "unknown",
        },
    )
    trace_store.add(
        session_id,
        "context_built",
        {
            "session_id": session_id,
            "intent": intent,
            "sources": context_report["sources"],
            "chosen_order_id": context_report["chosen_order_id"],
            "conflict_count": len(context_report["conflict_resolutions"]),
            "history_kept_count": compression_report["kept_count"],
            "history_dropped_count": compression_report["dropped_count"],
            "estimated_tokens": estimated_tokens,
        },
    )
    trace_store.add(
        session_id,
        "model_route_planned",
        {
            "session_id": session_id,
            "intent": intent,
            "used_model": route_result.used_model,
            "model_name": route_result.model_name,
            "fallback_reason": route_result.fallback_reason,
            "candidate_validated": route_result.candidate is not None,
            "candidate_intent": route_result.candidate.intent if route_result.candidate else None,
            "candidate_tools": route_result.candidate.required_tools if route_result.candidate else [],
            "candidate_domains": route_result.candidate.knowledge_domains if route_result.candidate else [],
        },
    )


def record_trace_events(session_id: str, events: tuple[tuple[str, dict[str, Any]], ...]) -> None:
    """把模块返回的公开 trace 事件统一写入 TraceStore。"""
    for event_type, payload in events:
        trace_store.add(session_id, event_type, payload)


def public_trace_summary(session_id: str, *, include_hidden_cot_flag: bool = True) -> dict[str, Any]:
    """生成响应中的公开 trace 摘要，不暴露 hidden CoT 或敏感原文。"""
    summary: dict[str, Any] = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "event_count": len(trace_store.list(session_id)),
        "public_trace_only": True,
    }
    if include_hidden_cot_flag:
        summary["hidden_cot_exposed"] = False
    return summary
