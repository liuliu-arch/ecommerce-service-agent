"""HITL 恢复与 checkpoint 层，保护高风险售后动作的恢复、复核和幂等。"""

from __future__ import annotations

from typing import Any, Literal
from course_runtime.course_logging import log_course_event

from api.schemas import *
from config.settings import TRACE_SCHEMA_VERSION
from integrations.ecommerce_client import order_fact_from_ecommerce
from observability.trace import public_trace_summary
from state.session_state import SUBMITTED_ACTIONS, WORKFLOW_CHECKPOINTS
from tools.runtime_context import logistics_status_from_order, order_no, order_status

def build_resume_token(session_id: str, workflow_id: str, order_id: str | None) -> str:
    """生成 HITL 恢复令牌，说明高风险 workflow 不能靠普通聊天继续执行。"""
    return f"resume-{session_id}-{workflow_id}-{order_id or 'missing'}"


def freeze_workflow_fields(request: ChatRequest, order: dict[str, Any] | None) -> dict[str, Any]:
    """冻结审批前的关键业务事实，恢复时用来检查订单状态是否漂移。"""
    return {
        "runtime_user_id": request.runtime_user_id,
        "order_id": order_no(order) if order else None,
        "order_status": order_status(order) if order else None,
        "logistics_status": logistics_status_from_order(order) if order else None,
    }


def business_recheck(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """恢复 workflow 前复核冻结事实，防止审批期间订单状态变化后继续执行。"""
    frozen = checkpoint["frozen_fields"]
    order_id = frozen.get("order_id")
    try:
        current_order = order_fact_from_ecommerce(order_id, str(frozen["runtime_user_id"])) if order_id else None
    except Exception:
        return {"passed": False, "reason": "business_api_unavailable", "mismatches": {}}
    if current_order is None:
        return {"passed": False, "reason": "order_not_found", "mismatches": {"order_id": {"frozen": order_id, "current": None}}}
    mismatches: dict[str, Any] = {}
    current_values = {
        "order_status": order_status(current_order),
        "logistics_status": logistics_status_from_order(current_order),
    }
    for field in ("order_status", "logistics_status"):
        if frozen.get(field) != current_values.get(field):
            mismatches[field] = {"frozen": frozen.get(field), "current": current_values.get(field)}
    return {"passed": not mismatches, "reason": None if not mismatches else "business_fact_drift", "mismatches": mismatches}


def build_refund_workflow_checkpoint(
    *,
    request: ChatRequest,
    order: dict[str, Any] | None,
    order_id: str | None,
    citations: list[Citation],
) -> dict[str, Any]:
    """组装并保存未发货退款 HITL checkpoint，Agent 只关心 workflow 摘要。"""
    workflow = {
        "workflow_id": f"wf-{request.session_id}",
        "workflow_type": "unshipped_refund",
        "status": "paused",
        "pending_action": "require_approval",
        "order_id": order_no(order) if order else order_id,
        "resume_token": build_resume_token(request.session_id, f"wf-{request.session_id}", order_id),
        "approval_id": f"appr-{request.session_id}",
        "idempotency_key": f"hitl:{request.session_id}:{order_id}",
        "frozen_fields": freeze_workflow_fields(request, order),
    }
    WORKFLOW_CHECKPOINTS[(request.session_id, workflow["workflow_id"])] = {
        "workflow": workflow,
        "frozen_fields": workflow["frozen_fields"],
        "resume_token": workflow["resume_token"],
        "idempotency_key": workflow["idempotency_key"],
        "citations": [citation.model_dump() for citation in citations],
        "order_snapshot": order,
    }
    return workflow


def blocked_resume_response(
    request: ChatResumeRequest,
    reason: str,
    trace_store: Any,
    business_recheck_payload: dict[str, Any] | None = None,
) -> ChatResumeResponse:
    """构造被阻断的恢复响应，把失败原因显式暴露给课程观察台。"""
    recheck = business_recheck_payload or {"passed": False, "reason": reason, "mismatches": {}}
    return ChatResumeResponse(
        session_id=request.session_id,
        workflow_id=request.workflow_id,
        status="blocked",
        answer="审批恢复没有通过校验，不能继续执行高风险售后动作。",
        resume_result={"accepted": False, "decision": request.decision, "idempotent_replay": False, "request_id": None, "reason": reason},
        workflow=None,
        business_recheck=recheck,
        session_state={
            "agent_version": "ecommerce-agent",
            "workflow": None,
            "trace": {"schema_version": TRACE_SCHEMA_VERSION, "event_count": len(trace_store.list(request.session_id)), "public_trace_only": True},
        },
    )


def resume_from_checkpoint(request: ChatResumeRequest, trace_store: Any) -> ChatResumeResponse:
    """恢复暂停的 HITL workflow，校验令牌、复核业务事实并保持幂等。"""
    checkpoint = WORKFLOW_CHECKPOINTS.get((request.session_id, request.workflow_id))
    log_course_event("RESUME_CHECKPOINT", "已查找待恢复工作流 Checkpoint", teaching=True, workflow_id=request.workflow_id, found=checkpoint is not None)
    if checkpoint is None:
        return blocked_resume_response(request, "checkpoint_not_found", trace_store)
    if checkpoint["resume_token"] != request.resume_token:
        log_course_event("RESUME_BLOCKED", "恢复令牌校验失败", teaching=True, reason="invalid_resume_token")
        return blocked_resume_response(request, "invalid_resume_token", trace_store)

    recheck = business_recheck(checkpoint)
    log_course_event("BUSINESS_RECHECK", "恢复前业务事实复核完成", teaching=True, passed=recheck.get("passed"), reason=recheck.get("reason"))
    if not recheck["passed"]:
        return blocked_resume_response(request, "business_fact_drift", trace_store, business_recheck_payload=recheck)

    workflow = dict(checkpoint["workflow"])
    idempotency_key = checkpoint["idempotency_key"]
    idempotent_replay = idempotency_key in SUBMITTED_ACTIONS
    log_course_event("IDEMPOTENCY_CHECK", "恢复请求已进入幂等保护", teaching=True, idempotency_key=idempotency_key, idempotent_replay=idempotent_replay, decision=request.decision)
    if request.decision == "approved":
        workflow["status"] = "completed"
        workflow["pending_action"] = "approval_accepted"
        answer = "售后主管已批准模拟退款申请，系统记录审批通过；本课程版本不执行真实资金退款。"
        status: Literal["completed", "paused", "rejected", "blocked"] = "completed"
        request_id = SUBMITTED_ACTIONS.setdefault(idempotency_key, {"request_id": f"refund-{request.workflow_id}"})["request_id"]
    elif request.decision == "rejected":
        workflow["status"] = "rejected"
        workflow["pending_action"] = "approval_rejected"
        answer = "售后主管已拒绝本次模拟退款申请，Agent 只能把结果告知用户，不能绕过人工审批。"
        status = "rejected"
        request_id = None
    else:
        workflow["status"] = "paused"
        workflow["pending_action"] = "need_more_info"
        answer = "售后主管要求补充信息，workflow 继续暂停，等待用户或客服补齐材料。"
        status = "paused"
        request_id = None

    trace_store.add(
        request.session_id,
        "workflow_resumed",
        {
            "session_id": request.session_id,
            "workflow_id": request.workflow_id,
            "pending_action": workflow["pending_action"],
            "status": status,
        },
    )
    trace_store.add(
        request.session_id,
        "human_approval_resolved",
        {
            "session_id": request.session_id,
            "workflow_id": request.workflow_id,
            "decision": request.decision,
            "reviewer_role": request.reviewer_role,
            "status": status,
        },
    )
    cost_summary = {
        "schema_version": "cost_summary_v1",
        "path_type": "hitl_resume_path",
        "model_calls": {"route_planner": 0, "final_answer": 0, "extra_reasoning": 0},
        "tool_call_count": 0,
        "business_tool_call_count": 0,
        "rag": {"needs_rag": False, "hit_count": 0, "cache_hit": False},
        "workflow": {"used_langgraph": True, "workflow_id": request.workflow_id, "hitl_required": False, "status": status},
        "safety_boundary": {
            "cost_control_does_not_skip_business_facts": True,
            "cost_control_does_not_skip_hitl": True,
            "not_finops_or_billing_system": True,
        },
    }
    trace_store.add(request.session_id, "cost_recorded", cost_summary)
    return ChatResumeResponse(
        session_id=request.session_id,
        workflow_id=request.workflow_id,
        status=status,
        answer=answer,
        resume_result={
            "accepted": True,
            "decision": request.decision,
            "idempotent_replay": idempotent_replay,
            "request_id": request_id,
            "reason": "approval_recorded",
        },
        workflow=workflow,
        business_recheck=recheck,
        session_state={
            "agent_version": "ecommerce-agent",
            "workflow": workflow,
            "cost_summary": cost_summary,
            "trace": public_trace_summary(request.session_id),
        },
    )
