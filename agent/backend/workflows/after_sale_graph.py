"""第 41 课真实 LangGraph 售后审批入口，保持现有 checkpoint/resume 契约。"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from course_runtime.course_logging import log_course_event

from api.schemas import ChatRequest, Citation
from tools.runtime_context import logistics_status_from_order, order_status
from workflows.resume import build_refund_workflow_checkpoint

def course_today() -> date:
    """使用实际业务日期；仅可复现的测试显式覆盖时钟。"""
    configured = os.getenv("AGENT_COURSE_TODAY")
    # Do not silently use a frozen teaching date in a running customer service.
    return date.fromisoformat(configured) if configured else date.today()


class RefundApprovalState(TypedDict, total=False):
    request: ChatRequest
    order: dict[str, Any] | None
    order_id: str | None
    citations: list[Citation]
    order_fact_status: str
    policy_ids: list[str]
    node_history: list[str]
    workflow: dict[str, Any]


class RefundApprovalGraph:
    """用三个显式节点展示事实、政策和 HITL checkpoint 如何串成售后流程。"""

    graph_name = "lesson41_refund_approval_graph"

    def __init__(self) -> None:
        graph = StateGraph(RefundApprovalState)
        graph.add_node("validate_order_fact", self._validate_order_fact)
        graph.add_node("attach_refund_policy", self._attach_refund_policy)
        graph.add_node("pause_for_human_approval", self._pause_for_human_approval)
        graph.set_entry_point("validate_order_fact")
        graph.add_edge("validate_order_fact", "attach_refund_policy")
        graph.add_edge("attach_refund_policy", "pause_for_human_approval")
        graph.add_edge("pause_for_human_approval", END)
        self.compiled_graph = graph.compile()

    def run(
        self,
        *,
        request: ChatRequest,
        order: dict[str, Any] | None,
        order_id: str | None,
        citations: list[Citation],
    ) -> dict[str, Any]:
        """运行 StateGraph，并返回与已发布 API 兼容的 workflow 摘要。"""
        eligible, reason = self.assess_eligibility(order)
        if not eligible:
            raise ValueError(reason)
        result = self.compiled_graph.invoke(
            {
                "request": request,
                "order": order,
                "order_id": order_id,
                "citations": citations,
                "node_history": [],
            }
        )
        return result["workflow"]

    @staticmethod
    def assess_eligibility(order: dict[str, Any] | None) -> tuple[bool, str]:
        """未发货退款必须同时满足订单存在、已支付且尚未发货。"""
        if order is None:
            return False, "order_not_verified"
        payment_status = str(order.get("paymentStatus") or order.get("payment_status") or "").upper()
        fulfillment = order_status(order).upper()
        logistics = logistics_status_from_order(order).upper()
        if payment_status and payment_status != "PAID":
            return False, "payment_not_paid"
        if fulfillment not in {"PAID_PENDING_SHIPMENT", "PENDING_SHIPMENT"} or logistics not in {"NOT_SHIPPED", "UNKNOWN"}:
            return False, "order_already_shipped_or_not_eligible"
        return True, "eligible"

    @staticmethod
    def _append_node(state: RefundApprovalState, node: str) -> list[str]:
        return [*state.get("node_history", []), node]

    def _validate_order_fact(self, state: RefundApprovalState) -> dict[str, Any]:
        log_course_event("WORKFLOW_NODE", "退款工作流已校验订单事实", teaching=True, node="validate_order_fact", verified=state.get("order") is not None)
        return {
            "order_fact_status": "verified" if state.get("order") is not None else "manual_review_required",
            "node_history": self._append_node(state, "validate_order_fact"),
        }

    def _attach_refund_policy(self, state: RefundApprovalState) -> dict[str, Any]:
        policy_ids = [
            str((citation.metadata or {}).get("policy_id"))
            for citation in state.get("citations", [])
            if (citation.metadata or {}).get("policy_id")
        ]
        log_course_event("WORKFLOW_NODE", "退款工作流已挂接政策依据", teaching=True, node="attach_refund_policy", policy_ids=policy_ids)
        return {
            "policy_ids": policy_ids,
            "node_history": self._append_node(state, "attach_refund_policy"),
        }

    def _pause_for_human_approval(self, state: RefundApprovalState) -> dict[str, Any]:
        workflow = build_refund_workflow_checkpoint(
            request=state["request"],
            order=state.get("order"),
            order_id=state.get("order_id"),
            citations=state.get("citations", []),
        )
        log_course_event("WORKFLOW_NODE", "退款工作流已保存 Checkpoint 并暂停等待人工审批", teaching=True, node="pause_for_human_approval", workflow_id=workflow["workflow_id"], approval_id=workflow["approval_id"])
        node_history = self._append_node(state, "pause_for_human_approval")
        workflow.update(
            {
                "used_langgraph": True,
                "graph_name": self.graph_name,
                "current_node": "pause_for_human_approval",
                "node_history": node_history,
                "order_fact_status": state.get("order_fact_status"),
                "policy_ids": state.get("policy_ids", []),
            }
        )
        return {"workflow": workflow, "node_history": node_history}


REFUND_APPROVAL_GRAPH = RefundApprovalGraph()


class ReceivedReturnState(TypedDict, total=False):
    order: dict[str, Any]
    order_id: str
    eligible: bool
    reason: str
    signed_days: int | None
    return_reason: str | None
    citations: list[Citation]
    policy_ids: list[str]
    node_history: list[str]
    workflow: dict[str, Any]


class ReceivedReturnGraph:
    """签收后退货只做资格准备，不自动提交或批准退货。"""

    graph_name = "lesson41_received_return_graph"

    def __init__(self) -> None:
        graph = StateGraph(ReceivedReturnState)
        graph.add_node("validate_received_order", self._validate_received_order)
        graph.add_node("check_return_window", self._check_return_window)
        graph.add_node("stop_before_return_submission", self._stop_before_submission)
        graph.set_entry_point("validate_received_order")
        graph.add_edge("validate_received_order", "check_return_window")
        graph.add_edge("check_return_window", "stop_before_return_submission")
        graph.add_edge("stop_before_return_submission", END)
        self.compiled_graph = graph.compile()

    def run(self, order: dict[str, Any], *, return_reason: str | None, citations: list[Citation]) -> dict[str, Any]:
        result = self.compiled_graph.invoke(
            {
                "order": order,
                "order_id": str(order.get("orderNo") or order.get("order_id")),
                "return_reason": return_reason,
                "citations": citations,
                "node_history": [],
            }
        )
        return result["workflow"]

    @staticmethod
    def _nodes(state: ReceivedReturnState, node: str) -> list[str]:
        return [*state.get("node_history", []), node]

    def _validate_received_order(self, state: ReceivedReturnState) -> dict[str, Any]:
        status = order_status(state["order"]).upper()
        received = status in {"DELIVERED", "SIGNED", "COMPLETED"}
        log_course_event("WORKFLOW_NODE", "签收后退货工作流已校验订单状态", teaching=True, node="validate_received_order", status=status, received=received)
        return {
            "eligible": received,
            "reason": "order_received" if received else "order_not_received",
            "node_history": self._nodes(state, "validate_received_order"),
        }

    def _check_return_window(self, state: ReceivedReturnState) -> dict[str, Any]:
        order = state["order"]
        raw_signed_at = order.get("deliveredAt") or order.get("signedAt") or order.get("signed_date")
        signed_days: int | None = None
        if raw_signed_at:
            try:
                signed_days = (course_today() - datetime.fromisoformat(str(raw_signed_at).replace("Z", "+00:00")).date()).days
            except ValueError:
                signed_days = None
        returnable = order.get("returnable")
        if returnable is None:
            item_returnability = [
                item.get("returnable")
                for item in order.get("items", [])
                if isinstance(item, dict)
            ]
            if item_returnability and all(value is True for value in item_returnability):
                returnable = True
            elif any(value is False for value in item_returnability):
                returnable = False
        has_reason = bool(state.get("return_reason"))
        eligible = bool(state.get("eligible")) and returnable is True and signed_days is not None and 0 <= signed_days <= 7 and has_reason
        if not state.get("eligible"):
            reason = "order_not_received"
        elif returnable is False:
            reason = "product_not_returnable"
        elif returnable is not True:
            reason = "product_returnability_unknown"
        elif signed_days is None:
            reason = "signed_time_missing"
        elif signed_days < 0:
            reason = "signed_time_in_future"
        elif signed_days > 7:
            reason = "return_window_expired"
        elif not has_reason:
            reason = "return_reason_missing"
        else:
            reason = "eligible_for_application"
        log_course_event("WORKFLOW_NODE", "签收后退货窗口与商品属性检查完成", teaching=True, node="check_return_window", eligible=eligible, reason=reason, signed_days=signed_days)
        return {
            "eligible": eligible,
            "reason": reason,
            "signed_days": signed_days,
            "node_history": self._nodes(state, "check_return_window"),
        }

    def _stop_before_submission(self, state: ReceivedReturnState) -> dict[str, Any]:
        eligible = bool(state.get("eligible"))
        nodes = self._nodes(state, "stop_before_return_submission")
        policy_ids = [
            str((citation.metadata or {}).get("policy_id"))
            for citation in state.get("citations", [])
            if (citation.metadata or {}).get("policy_id")
        ]
        workflow = {
            "workflow_id": f"return-{state['order_id']}",
            "workflow_type": "received_return",
            "used_langgraph": True,
            "graph_name": self.graph_name,
            "current_node": "stop_before_return_submission",
            "node_history": nodes,
            "status": "paused" if eligible else "blocked",
            "pending_action": "prepare_return_application" if eligible else "explain_boundary",
            "eligibility_status": "eligible_for_application" if eligible else "not_eligible",
            "eligibility_reason": state.get("reason"),
            "signed_days": state.get("signed_days"),
            "return_reason": state.get("return_reason"),
            "policy_ids": policy_ids,
            "evidence_checklist": ["订单状态", "物流状态", "售后政策依据", "签收时间", "商品可退属性", "退货原因"],
            "needs_human_approval": eligible,
        }
        log_course_event("WORKFLOW_NODE", "签收后退货流程已停在提交前边界", teaching=True, node="stop_before_return_submission", status=workflow["status"], pending_action=workflow["pending_action"])
        return {"workflow": workflow, "node_history": nodes}


RECEIVED_RETURN_GRAPH = ReceivedReturnGraph()
