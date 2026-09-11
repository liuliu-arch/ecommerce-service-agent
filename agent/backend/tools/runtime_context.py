"""Runtime Context 工具函数，负责从当前用户上下文里读取订单事实并保护归属边界。"""

from __future__ import annotations

from typing import Any

from api.schemas import *


def runtime_context_summary(request: ChatRequest) -> dict[str, Any]:
    """返回前端可观察的 Runtime Context 摘要，区分模型可见和系统边界字段。"""
    return {
        "user_id": request.runtime_user_id,
        "nickname": request.runtime_nickname,
        "member_level": request.runtime_member_level,
        "risk_level": request.runtime_risk_level,
        "trusted_for_model": {
            "nickname": request.runtime_nickname,
            "member_level": request.runtime_member_level,
        },
        "system_only": {
            "user_id": request.runtime_user_id,
            "risk_level": request.runtime_risk_level,
        },
        "source": "request_runtime_context",
    }


def is_runtime_identity_query(user_message: str) -> bool:
    """识别需要直接读取当前登录 Runtime Context 的身份问题。"""
    normalized = user_message.strip().replace("？", "?")
    return any(
        keyword in normalized
        for keyword in (
            "我是谁",
            "我现在是谁",
            "当前用户是谁",
            "当前登录用户",
            "我的账号",
            "我的用户",
            "我的身份",
            "会员等级",
            "我是什么会员",
        )
    )


def runtime_identity_answer(request: ChatRequest) -> str:
    """用系统注入的 Runtime Context 回答身份问题，不从用户文本里猜身份。"""
    nickname = request.runtime_nickname or "当前用户"
    member_level = request.runtime_member_level or "unknown"
    risk_level = request.runtime_risk_level or "unknown"
    return (
        f"你当前登录的是 {nickname}，会员等级是 "
        f"{ {'gold':'金卡','silver':'银卡','normal':'普通会员'}.get(member_level,member_level) }。"
        "该等级以当前登录账户的信息为准。"
    )


def general_chat_answer(user_message: str) -> str:
    """普通咨询也要返回可直接给用户看的客服话术，不能暴露调试占位说明。"""
    normalized = user_message.strip().replace("？", "?")
    if any(keyword in normalized for keyword in ("你是谁", "你是什么", "你能做什么", "介绍一下你")):
        return (
            "我是电商公司的客服 Agent，可以帮你查询订单物流、解释活动和会员规则，"
            "也可以协助发起退款等售后流程。涉及退款、补偿、取消订单等高风险操作时，"
            "我会先核对业务事实，并按流程等待人工审批。"
        )
    return (
        "你好，我是电商公司的客服 Agent。你可以把订单号、物流问题、活动优惠或售后诉求发给我，"
        "我会优先根据电商公司的订单事实和公开规则回答。"
    )

def as_order_list(value: Any) -> list[dict[str, Any]]:
    """兼容 runtime_context 中的当前用户订单列表，只保留字典型订单快照。"""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def order_no(order: dict[str, Any]) -> str:
    """从不同字段命名中读取订单号，保护课程快照和业务 DTO 的边界。"""
    return str(order.get("orderNo") or order.get("order_id") or "").strip()


def order_user_id(order: dict[str, Any]) -> str:
    """读取订单归属用户，用于防止跨账号订单被工具或上下文误用。"""
    return str(order.get("userId") or order.get("user_id") or "").strip()


def order_status(order: dict[str, Any]) -> str:
    """归一化履约状态，让售后 workflow 能用稳定字段判断风险路径。"""
    value = str(
        order.get("fulfillmentStatus")
        or order.get("fulfillment_status")
        or order.get("orderStatus")
        or order.get("order_status")
        or order.get("status")
        or ""
    ).strip()
    if value.upper() in {"PAID_PENDING_SHIPMENT", "PENDING_PAYMENT_CONFIRMATION", "UNSHIPPED", "NOT_SHIPPED"}:
        return "PENDING_SHIPMENT"
    return value


def order_status_label(order: dict[str, Any]) -> str:
    """把订单履约枚举转成用户能直接理解的客服口径。"""
    status = order_status(order).upper()
    labels = {
        "PENDING_PAYMENT": "待付款",
        "PENDING_SHIPMENT": "待发货",
        "PAID_PENDING_SHIPMENT": "待发货",
        "PENDING_PAYMENT_CONFIRMATION": "待发货",
        "UNSHIPPED": "待发货",
        "NOT_SHIPPED": "待发货",
        "SHIPPED": "已发货",
        "IN_TRANSIT": "运输中",
        "DELIVERED": "已送达",
        "SIGNED": "已签收",
        "COMPLETED": "已完成",
        "CANCELED": "已取消",
        "CANCELLED": "已取消",
        "REFUNDING": "退款处理中",
        "REFUNDED": "已退款",
    }
    return labels.get(status, status or "未知")


def logistics_status_from_order(order: dict[str, Any]) -> str:
    """从订单快照推断物流状态，实时系统不可用时也只给安全摘要。"""
    direct_value = str(order.get("logisticsStatus") or order.get("logistics_status") or "").strip()
    if direct_value:
        return direct_value
    fulfillment = order_status(order).upper()
    if fulfillment in {"PENDING_SHIPMENT", "NOT_SHIPPED", "UNSHIPPED"}:
        return "NOT_SHIPPED"
    if fulfillment in {"SHIPPED", "IN_TRANSIT"}:
        return "IN_TRANSIT"
    if fulfillment in {"DELIVERED", "SIGNED"}:
        return "SIGNED"
    return fulfillment or "UNKNOWN"


def logistics_status_label(order: dict[str, Any]) -> str:
    """把物流枚举转成面向用户的自然中文状态。"""
    status = logistics_status_from_order(order).upper()
    labels = {
        "NOT_SHIPPED": "暂未发货",
        "PENDING_SHIPMENT": "暂未发货",
        "SHIPPED": "已发货",
        "IN_TRANSIT": "运输中",
        "DELIVERED": "已送达",
        "SIGNED": "已签收",
        "EXCEPTION": "物流异常",
        "UNKNOWN": "暂未查询到明确物流状态",
    }
    return labels.get(status, status or "暂未查询到明确物流状态")


def item_names(order: dict[str, Any]) -> list[str]:
    """提取订单商品名，供工具摘要、Trace 和回答使用。"""
    raw_items = order.get("items")
    if isinstance(raw_items, list):
        names: list[str] = []
        for item in raw_items:
            if isinstance(item, dict):
                name = str(item.get("productName") or item.get("name") or "").strip()
                if name:
                    names.append(name)
            elif isinstance(item, str):
                names.append(item)
        if names:
            return names
    return ["商品明细以订单系统为准"]


def find_context_order(context: dict[str, Any] | None, target_order_no: str) -> dict[str, Any] | None:
    """只在当前用户上下文中查找订单，避免凭用户输入订单号越权。"""
    if not isinstance(context, dict):
        return None
    target = target_order_no.lower()
    for order in as_order_list(context.get("currentUserOrders")):
        if order_no(order).lower() == target:
            return order
    return None
