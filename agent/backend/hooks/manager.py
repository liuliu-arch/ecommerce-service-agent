"""在工具调用前后、错误和完成阶段生成公开治理事件。"""

from __future__ import annotations

from typing import Any

from api.schemas import ToolCallTrace
from course_runtime.course_logging import log_course_event, log_tool_finished, log_tool_started


class HookManager:
    """Hook 负责统一治理和观察，不负责替代 Tool 或批准高风险动作。"""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.touched_tools: list[str] = []

    def pre_tool_call(self, tool_name: str, arguments: dict[str, Any], runtime_user_id: str) -> None:
        required_argument = {
            "get_order_detail": "order_id",
            "get_order_logistics": "order_id",
            "get_refund_status": "order_id",
            "search_products": "keyword",
        }.get(tool_name)
        arguments_valid = bool(arguments.get(required_argument)) if required_argument else bool(arguments)
        log_tool_started(tool_name, arguments)
        log_course_event(
            "TOOL_RUNTIME_GUARD",
            "调用前 Hook 已校验必填参数和可信 Runtime Context 身份",
            teaching=True,
            tool_name=tool_name,
            arguments_valid=arguments_valid,
            argument_keys=sorted(arguments),
            runtime_identity_present=bool(runtime_user_id),
        )
        self.touched_tools.append(tool_name)
        self.events.append(
            {
                "hook_type": "pre_tool_call",
                "target_name": tool_name,
                "action": "validate_arguments_and_runtime_identity",
                "status": "allowed" if arguments_valid else "needs_clarification",
                "argument_keys": sorted(arguments),
                "runtime_user_id": runtime_user_id,
                "redacted": True,
            }
        )

    def post_tool_call(self, call: ToolCallTrace) -> None:
        log_tool_finished(call.tool_name, call)
        log_course_event(
            "TOOL_OBSERVATION_GOVERNED",
            "工具结果已转换为受控 Observation，下一步只读取治理后的摘要",
            teaching=True,
            tool_name=call.tool_name,
            status=call.status,
            risk_level=call.risk_level,
            next_action=call.next_action,
            error_type=call.error_type,
            observation_summary=call.output_summary,
        )
        self.events.append(
            {
                "hook_type": "post_tool_call",
                "target_name": call.tool_name,
                "action": "sanitize_observation",
                "status": call.status,
                "risk_level": call.risk_level,
                "next_action": call.next_action,
                "redacted": True,
            }
        )
        if call.status == "error":
            self.events.append(
                {
                    "hook_type": "on_error",
                    "target_name": call.tool_name,
                    "action": "normalize_error_for_degradation",
                    "status": "degraded",
                    "error_type": call.error_type,
                    "redacted": True,
                }
            )

    def on_completion(self, *, risk_level: str, next_action: str, degraded: bool) -> dict[str, Any]:
        event = {
            "hook_type": "on_completion",
            "target_name": "chat_request",
            "action": "summarize_tool_governance",
            "status": "completed",
            "risk_level": risk_level,
            "next_action": next_action,
            "degraded": degraded,
            "redacted": True,
        }
        self.events.append(event)
        degraded_count = sum(event.get("status") == "degraded" for event in self.events)
        return {
            "hook_count": len(self.events),
            "tool_count": len(self.touched_tools),
            "touched_tools": list(self.touched_tools),
            "degraded": degraded,
            "redacted_count": sum(bool(event.get("redacted")) for event in self.events),
            "degraded_count": max(int(degraded), degraded_count),
            "risk_hit_count": sum(event.get("risk_level") in {"medium", "high"} for event in self.events),
        }
