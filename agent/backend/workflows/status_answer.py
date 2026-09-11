"""Render after-sale states without allowing a language model to advance them."""

from typing import Any


def workflow_status_answer(workflow: dict[str, Any] | None) -> str | None:
    """Only internal state combinations authorize a specific status statement.

    This course has no real submission receipt integration. In particular, an
    approval_id or a completed simulation never authorizes 'refund submitted'.
    """
    if not workflow:
        return None
    kind = workflow.get("workflow_type")
    state = (workflow.get("status"), workflow.get("pending_action"))
    if kind == "unshipped_refund":
        if state == ("paused", "require_approval"):
            return (
                "该订单符合未发货退款申请条件。当前流程已暂停，等待人工审批。"
                "目前仅记录待审批状态，尚未向业务系统提交退款申请，也未执行退款。"
                "请联系人工客服核验并继续处理。"
            )
        if state == ("completed", "approval_accepted"):
            return "模拟退款审批已通过；本课程不执行真实资金退款，也不代表退款已经到账。"
        if state == ("rejected", "approval_rejected"):
            return "本次模拟退款申请被拒绝，不能继续执行退款；请联系人工客服了解原因。"
        if state == ("paused", "need_more_info"):
            return "当前审批需要补充信息，流程继续暂停。请联系人工客服确认所需材料；尚未执行退款。"
    elif kind == "received_return":
        eligibility = workflow.get("eligibility_status")
        if state == ("paused", "prepare_return_application") and eligibility == "eligible_for_application":
            return (
                "根据已核验的订单事实和售后政策，您可以准备退货申请。"
                "当前流程停在提交前，尚未代您准备或提交申请，当前还不是退货成功。"
                "请联系人工客服确认所需材料，后续退货结果仍需人工审核。"
            )
        if state == ("blocked", "explain_boundary") and eligibility == "not_eligible":
            return "当前订单未通过退货申请资格校验，不能按此流程继续提交；请联系人工客服核验具体原因。"
    # New or inconsistent states require an explicit mapping before being shown
    # as a successful action. Never feed an unknown workflow back to free text.
    return "当前售后流程状态需要人工核验，暂时无法确认申请是否提交或处理完成。请联系人工客服核验。"
