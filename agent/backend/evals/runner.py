"""评测执行层，用固定用例检查回答、工具、引用、Trace 和状态。"""

from __future__ import annotations

from course_runtime.course_logging import log_course_event, observe_evaluation

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.customer_service_agent import Lesson41Agent
from api.schemas import *
from observability.trace import trace_store

class EvalRunner:
    """课程型离线回归评测。

    Eval 不读 hidden CoT，也不让测试伪造模型或工具结果；它只调用本课真实 Agent，
    再检查公开响应字段和 trace 事件是否满足固定 case 的结构化期望。
    """

    def __init__(self, agent: Lesson41Agent, cases_path: Path) -> None:
        """初始化本课服务对象，把可替换依赖固定在实例上，便于总演习和测试复用。"""
        self.agent = agent
        self.cases_path = cases_path
        self.backfilled_cases: list[dict[str, Any]] = []

    def load_cases(self) -> list[dict[str, Any]]:
        """读取固定评测用例，并合并从反馈回填的临时回归 case。"""
        payload = yaml.safe_load(self.cases_path.read_text(encoding="utf-8"))
        return [*payload["cases"], *self.backfilled_cases]

    @observe_evaluation
    def run(self, case_id: str | None = None) -> EvalRunResponse:
        """运行大促总演习回归评测，用公开响应、工具、引用、Trace 和状态检查退化。"""
        selected = [case for case in self.load_cases() if case_id in (None, case["case_id"])]
        results: list[EvalCaseResult] = []
        run_id = uuid4().hex[:8]
        for case in selected:
            session_id = f"eval-{case['case_id']}-{run_id}"
            actual = self._run_case(case, session_id)
            # 结构化公开信号继续精确匹配；最终客服话术允许不改变事实的等价改写，
            # 因此交给 expected_answer_claims 做受控校验，避免因字词增减而误判为回归失败。
            missing_signals = [signal for signal in case.get("expected_signals", []) if signal not in actual["text"]]
            missing_signals.extend(
                self._missing_answer_claims(actual["answer"], case.get("expected_answer_claims", []))
            )
            missing_tools = [tool for tool in case.get("expected_tools", []) if tool not in actual["tools"]]
            unexpected_tools = [tool for tool in case.get("forbidden_tools", []) if tool in actual["tools"]]
            missing_citations = [
                item for item in case.get("expected_citations", []) if not self._contains_any(actual["citations"], item)
            ]
            forbidden_citation_hits = [
                item for item in case.get("forbidden_citations", []) if self._contains_any(actual["citations"], item)
            ]
            missing_trace_events = [
                event for event in case.get("expected_trace_events", []) if event not in actual["trace_events"]
            ]
            missing_session_state = [
                requirement
                for requirement in case.get("expected_session_state", [])
                if not self._matches_session_state(actual["session_state"], requirement)
            ]
            forbidden_text_hits = [text for text in case.get("forbidden_text", []) if text in actual["text"]]
            forbidden_text_hits.extend(
                self._matched_answer_claims(actual["answer"], case.get("forbidden_answer_claims", []))
            )
            failure_categories = self._failure_categories(
                missing_signals=missing_signals,
                missing_tools=missing_tools,
                unexpected_tools=unexpected_tools,
                missing_citations=missing_citations,
                forbidden_citation_hits=forbidden_citation_hits,
                missing_trace_events=missing_trace_events,
                missing_session_state=missing_session_state,
                forbidden_text_hits=forbidden_text_hits,
            )
            results.append(
                EvalCaseResult(
                    case_id=case["case_id"],
                    passed=not failure_categories,
                    user_message=case.get("user_message", case["case_id"]),
                    expected_signals=case.get("expected_signals", []),
                    actual_answer=actual["answer"],
                    actual_tools=actual["tools"],
                    missing_signals=missing_signals,
                    actual_citations=actual["citations"],
                    actual_trace_events=actual["trace_events"],
                    missing_tools=missing_tools,
                    unexpected_tools=unexpected_tools,
                    missing_citations=missing_citations,
                    forbidden_citation_hits=forbidden_citation_hits,
                    missing_trace_events=missing_trace_events,
                    missing_session_state=missing_session_state,
                    forbidden_text_hits=forbidden_text_hits,
                    failure_categories=failure_categories,
                )
            )
            log_course_event("EVAL_CASE", "Evaluation Case 执行完成", case_id=case["case_id"], passed=results[-1].passed, failure_categories=results[-1].failure_categories)
        passed = len([result for result in results if result.passed])
        return EvalRunResponse(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            summary=self._summary(results),
            results=results,
        )

    def _run_case(self, case: dict[str, Any], session_id: str) -> dict[str, Any]:
        """按 case 类型运行聊天或 HITL 恢复，并统一成 Eval 可检查的公开信号。"""
        if case.get("case_type") == "resume":
            return self._run_resume_case(case, session_id)
        return self._run_chat_case(case, session_id)

    def _run_chat_case(self, case: dict[str, Any], session_id: str) -> dict[str, Any]:
        """运行普通 /chat case，并抽取固定评测信号。"""
        response = self.agent.chat(
            ChatRequest(
                session_id=session_id,
                runtime_user_id=case.get("runtime_user_id", "U1001"),
                runtime_nickname=case.get("runtime_nickname"),
                runtime_member_level=case.get("runtime_member_level"),
                runtime_risk_level=case.get("runtime_risk_level"),
                user_message=case["user_message"],
                runtime_context=case.get("runtime_context"),
            )
        )
        trace_events = trace_store.list(session_id)
        actual_tools = [call.tool_name for call in response.tool_calls]
        actual_citations = self._citation_signals(response.citations)
        actual_trace_events = [event.event_type for event in trace_events]
        actual_text = " ".join(
            [response.answer]
            + response.reasoning_summary
            + actual_tools
            + actual_citations
            + actual_trace_events
            + self._flatten_values(response.session_state)
        )
        return {
            "answer": response.answer,
            "tools": actual_tools,
            "citations": actual_citations,
            "trace_events": actual_trace_events,
            "session_state": response.session_state,
            "text": actual_text,
        }

    def _run_resume_case(self, case: dict[str, Any], session_id: str) -> dict[str, Any]:
        """运行 HITL 恢复类 case，让 /eval/run 也能覆盖恢复令牌、checkpoint 和幂等边界。"""
        start_response: ChatResponse | None = None
        workflow_id = case.get("workflow_id", f"wf-{session_id}")
        resume_token = case.get("resume_token", f"resume-{session_id}-{workflow_id}-missing")

        if case.get("start_user_message"):
            response = self.agent.chat(
                ChatRequest(
                    session_id=session_id,
                    runtime_user_id=case.get("runtime_user_id", "U1001"),
                    runtime_nickname=case.get("runtime_nickname"),
                    runtime_member_level=case.get("runtime_member_level"),
                    runtime_risk_level=case.get("runtime_risk_level"),
                    user_message=case["start_user_message"],
                    runtime_context=case.get("runtime_context"),
                )
            )
            start_response = response
            workflow = response.session_state.get("workflow") or {}
            workflow_id = workflow.get("workflow_id", workflow_id)
            resume_token = workflow.get("resume_token", resume_token)

        if case.get("resume_token_override") == "invalid":
            resume_token = f"invalid-{resume_token}"

        resume_request = ChatResumeRequest(
            session_id=session_id,
            workflow_id=workflow_id,
            resume_token=resume_token,
            reviewer_id=case.get("reviewer_id", "manager-01"),
            reviewer_role=case.get("reviewer_role", "after_sale_manager"),
            decision=case.get("decision", "approved"),
            reviewer_note=case.get("reviewer_note"),
        )
        response = self.agent.resume(resume_request)
        if case.get("repeat_resume"):
            response = self.agent.resume(resume_request)

        trace_events = trace_store.list(session_id)
        actual_trace_events = [event.event_type for event in trace_events]
        session_state = {
            **response.session_state,
            "resume_result": response.resume_result,
            "business_recheck": response.business_recheck,
            "resume_status": response.status,
        }
        actual_citations = self._citation_signals(start_response.citations) if start_response else []
        actual_text = " ".join(
            [response.answer]
            + actual_citations
            + actual_trace_events
            + self._flatten_values(response.resume_result)
            + self._flatten_values(response.business_recheck)
            + self._flatten_values(session_state)
        )
        return {
            "answer": response.answer,
            "tools": [],
            "citations": actual_citations,
            "trace_events": actual_trace_events,
            "session_state": session_state,
            "text": actual_text,
        }

    @staticmethod
    def _citation_signals(citations: list[Citation]) -> list[str]:
        """把引用对象展平成可匹配信号，便于规则化评测检查来源。"""
        signals: list[str] = []
        for citation in citations:
            signals.extend([citation.source, citation.title, citation.retrieval_stage or ""])
            if citation.metadata:
                signals.extend(str(value) for value in citation.metadata.values())
        return [signal for signal in signals if signal]

    @classmethod
    def _flatten_values(cls, value: Any) -> list[str]:
        """展开嵌套 session_state，用于匹配 workflow、Trace 和成本治理状态。"""
        if isinstance(value, dict):
            values: list[str] = []
            for item in value.values():
                values.extend(cls._flatten_values(item))
            return values
        if isinstance(value, list):
            values: list[str] = []
            for item in value:
                values.extend(cls._flatten_values(item))
            return values
        if value is None:
            return []
        return [str(value)]

    @staticmethod
    def _contains_any(values: list[str], expected: str) -> bool:
        """检查实际信号是否包含期望片段，避免评测依赖全文相等。"""
        return any(expected in value for value in values)

    @classmethod
    def _missing_answer_claims(cls, answer: str, claims: list[dict[str, str]]) -> list[str]:
        """允许模型改写客服话术，但仍要求关键事实按受控模式出现在最终回答中。"""
        return [cls._claim_label(claim) for claim in claims if not cls._matches_answer_claim(answer, claim)]

    @classmethod
    def _matched_answer_claims(cls, answer: str, claims: list[dict[str, str]]) -> list[str]:
        """识别越权承诺等禁止语义；放宽措辞不能放松业务安全边界。"""
        return [cls._claim_label(claim) for claim in claims if cls._matches_answer_claim(answer, claim)]

    @staticmethod
    def _matches_answer_claim(answer: str, claim: dict[str, str]) -> bool:
        pattern = claim.get("pattern", "")
        return bool(pattern and re.search(pattern, answer, flags=re.IGNORECASE))

    @staticmethod
    def _claim_label(claim: dict[str, str]) -> str:
        return claim.get("label") or claim.get("pattern") or "未命名回答断言"

    @classmethod
    def _matches_session_state(cls, session_state: dict[str, Any], requirement: str) -> bool:
        """按点路径检查 session_state，确认关键业务状态没有丢失。"""
        if "=" not in requirement:
            return cls._lookup(session_state, requirement) is not None
        path, expected = requirement.split("=", 1)
        actual = cls._lookup(session_state, path.strip())
        return cls._normalize_scalar(actual) == expected.strip()

    @staticmethod
    def _lookup(payload: dict[str, Any], path: str) -> Any:
        """在嵌套字典中读取点路径字段，服务于 Eval 的状态断言。"""
        current: Any = payload
        normalized_path = path.removeprefix("session_state.")
        for part in normalized_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @staticmethod
    def _normalize_scalar(value: Any) -> str:
        """把布尔和空值归一成字符串，让 YAML 期望更稳定。"""
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return "null"
        return str(value)

    @staticmethod
    def _failure_categories(
        *,
        missing_signals: list[str],
        missing_tools: list[str],
        unexpected_tools: list[str],
        missing_citations: list[str],
        forbidden_citation_hits: list[str],
        missing_trace_events: list[str],
        missing_session_state: list[str],
        forbidden_text_hits: list[str],
    ) -> list[str]:
        """把缺失项归并成问题类别，为反馈归因提供入口。"""
        categories: list[str] = []
        if missing_signals:
            categories.append("answer_signal_missing")
        if missing_tools or unexpected_tools:
            categories.append("tool_path_mismatch")
        if missing_citations or forbidden_citation_hits:
            categories.append("citation_missing")
        if missing_trace_events:
            categories.append("trace_event_missing")
        if missing_session_state:
            categories.append("session_state_mismatch")
        if forbidden_text_hits:
            categories.append("forbidden_text_present")
        return categories

    @staticmethod
    def _summary(results: list[EvalCaseResult]) -> dict[str, Any]:
        """汇总一次评测运行结果，展示失败 case 和失败类别。"""
        failed_cases = [result.case_id for result in results if not result.passed]
        failure_categories: dict[str, int] = {}
        for result in results:
            for category in result.failure_categories:
                failure_categories[category] = failure_categories.get(category, 0) + 1
        return {
            "schema_version": "eval_report_v1",
            "failed_cases": failed_cases,
            "failure_categories": failure_categories,
            "checked_dimensions": ["answer", "tool_calls", "citations", "trace", "session_state", "workflow", "hitl_resume"],
            "boundary": "规则化离线评测用于课程项目回归，不等同于线上监控、人工抽检或 LLM-as-judge 平台。",
        }
