"""轻量规划工具。这里展示课程版路由、订单号抽取和 token 估算。"""

from __future__ import annotations

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

from api.schemas import *


_CLAUSE_BOUNDARY_RE = re.compile(r"[\n，,。！？!?；;：:]")
_NEGATION_MARKERS = (
    "不要",
    "不用",
    "无需",
    "不必",
    "别",
    "暂不",
    "先不",
    "不想",
    "不是要",
    "并不想",
)
_FUTURE_HYPOTHETICAL_MARKERS = (
    "如果以后",
    "如果将来",
    "假如以后",
    "假如将来",
    "以后",
    "将来",
    "有一天",
)
_EXPLANATION_MARKERS = (
    "是什么意思",
    "什么情况下",
    "一般怎么处理",
    "通常怎么处理",
    "一般怎么规定",
    "怎么操作",
    "如何操作",
    "怎么申请",
    "如何申请",
    "流程是什么",
    "流程有哪些",
    "规则是什么",
    "政策是什么",
)
_DIRECT_REQUEST_MARKERS = (
    "我要",
    "我想",
    "帮我",
    "给我",
    "替我",
    "直接",
    "马上",
    "立即",
    "现在就",
)
_REFUND_STATUS_MARKERS = (
    "进度",
    "状态",
    "情况",
    "处理到哪",
    "到哪了",
    "什么时候到账",
    "怎么样",
    "结果",
    "是否到账",
    "到账了吗",
    "还没到账",
    "没收到",
    "审核",
    "是否通过",
    "有没有通过",
    "通过了吗",
    "成功了吗",
    "完成了吗",
    "被拒",
    "驳回",
    "退了吗",
    "帮我看看",
)

# Python 的 \b 会把中文和英文字母都视为“单词字符”，因此“订单SO...”这类
# 自然输入无法形成单词边界。这里改为只约束订单号自身允许的 ASCII 字符，
# 既支持中文紧邻订单号，也避免从更长的英文标识符中截取一段伪订单号。
_ORDER_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:SO[A-Za-z0-9_-]{6,}|ORD\d{4,})(?![A-Za-z0-9_-])",
    flags=re.IGNORECASE,
)


def _clause_bounds(user_message: str, position: int) -> tuple[int, int]:
    """只在当前分句内判断否定和请求语气，避免前一句误伤后一句。"""
    previous_boundaries = [match.end() for match in _CLAUSE_BOUNDARY_RE.finditer(user_message[:position])]
    following_boundary = _CLAUSE_BOUNDARY_RE.search(user_message, position)
    return (
        previous_boundaries[-1] if previous_boundaries else 0,
        following_boundary.start() if following_boundary else len(user_message),
    )


def _is_explanation(user_message: str) -> bool:
    return any(marker in user_message for marker in _EXPLANATION_MARKERS)


def _contains_asserted_term(user_message: str, terms: tuple[str, ...]) -> bool:
    """识别真正提出的动作；否定、未来假设和概念解释不触发确定性 guard。"""
    explanation = _is_explanation(user_message)
    for term in terms:
        for match in re.finditer(re.escape(term), user_message):
            clause_start, clause_end = _clause_bounds(user_message, match.start())
            clause = user_message[clause_start:clause_end]
            prefix = user_message[clause_start:match.start()].strip()
            nearby_prefix = prefix[-12:]
            if any(marker in nearby_prefix for marker in _NEGATION_MARKERS):
                continue
            # “不退款”是否定；“能不能退款”是资格询问，不能被其中的“不”误伤。
            if re.search(
                r"(?:^|我|先|暂时|现在)不(?:再|想|要|用|需|必|打算|准备|需要)?$",
                nearby_prefix,
            ):
                continue
            if any(marker in clause for marker in _FUTURE_HYPOTHETICAL_MARKERS):
                continue
            if explanation and any(marker in prefix for marker in ("如果", "假如", "假设")):
                continue
            if explanation and not any(marker in clause for marker in _DIRECT_REQUEST_MARKERS):
                continue
            return True
    return False


def _is_existing_refund_request(user_message: str) -> bool:
    return any(
        marker in user_message
        for marker in (
            "已经申请退款",
            "已申请退款",
            "申请过退款",
            "提交了退款申请",
            "退款申请已提交",
            "已经发起退款",
            "发起过退款",
            "刚取消订单",
            "已经取消订单",
        )
    )


def _is_existing_return_request(user_message: str) -> bool:
    return any(
        marker in user_message
        for marker in (
            "已经申请退货",
            "已申请退货",
            "申请过退货",
            "提交了退货申请",
            "退货申请已提交",
            "已经寄回",
            "已经退货",
        )
    )


def _is_explicit_degradation(user_message: str) -> bool:
    if "SERVICE_TIMEOUT" not in user_message:
        return False
    if "故障注入" in user_message or ("模拟" in user_message and "返回" in user_message):
        return True
    if _is_explanation(user_message):
        return False
    return any(
        marker in user_message
        for marker in ("报错", "异常", "失败", "超时", "不可用", "遇到", "出现", "返回")
    )


def classify_guard_intent(user_message: str) -> Intent | None:
    """只识别足够明确、允许覆盖模型路由的确定性边界。"""
    if _is_explicit_degradation(user_message):
        return "degradation_request"
    if _contains_asserted_term(
        user_message,
        ("系统提示词", "hidden reasoning", "隐藏推理", "工具 schema", "内部策略"),
    ):
        return "security_request"
    if not _is_existing_return_request(user_message) and _contains_asserted_term(
        user_message,
        (
            "我要退货",
            "我想退货",
            "我要申请退货",
            "我想申请退货",
            "帮我退货",
            "帮我申请退货",
            "给我退货",
            "直接退货",
        ),
    ):
        return "return_request"
    if _contains_asserted_term(
        user_message,
        (
            "我要退款",
            "我想退款",
            "我要申请退款",
            "我想申请退款",
            "帮我退款",
            "帮我申请退款",
            "给我退款",
            "直接退款",
            "直接给我退",
            "把钱退给我",
        ),
    ):
        return "refund_request"
    if _contains_asserted_term(user_message, ("退款", "退钱")) and any(
        term in user_message for term in _REFUND_STATUS_MARKERS
    ):
        return "refund_status_query"
    if not _is_existing_return_request(user_message) and _contains_asserted_term(
        user_message,
        (
            "申请退货",
            "七天无理由",
            "寄回",
            "能退货吗",
            "可以退货吗",
        ),
    ):
        return "return_request"
    if not _is_existing_refund_request(user_message) and _contains_asserted_term(
        user_message,
        (
            "申请退款",
            "发起退款",
            "办理退款",
            "退钱",
            "取消订单",
            "能退款吗",
            "可以退款吗",
            "还能退款吗",
            "能不能退款",
        ),
    ):
        return "refund_request"
    return None


def classify_intent(user_message: str) -> Intent:
    """用可读规则做总演习路由，展示 Tool、RAG、Workflow、降级和安全分流入口。"""
    guard_intent = classify_guard_intent(user_message)
    if guard_intent is not None:
        return guard_intent
    # 模型不可用时仍提供课程兜底；这些宽泛关键词不能反向覆盖有效的模型判断。
    if _is_explanation(user_message) and any(term in user_message for term in ("退款", "退货", "取消订单")):
        return "general_chat"
    degradation_terms = ("SERVICE_TIMEOUT", "服务抽风", "工具超时", "接口不可用")
    if _is_explanation(user_message) and any(term in user_message for term in degradation_terms):
        return "general_chat"
    if any(term in user_message for term in degradation_terms[1:]):
        return "degradation_request"
    if (
        not _is_existing_return_request(user_message)
        and not _is_explanation(user_message)
        and _contains_asserted_term(user_message, ("退货",))
    ):
        return "return_request"
    if (
        not _is_existing_refund_request(user_message)
        and not _is_explanation(user_message)
        and _contains_asserted_term(user_message, ("退款", "退钱"))
    ):
        return "refund_request"
    if any(term in user_message for term in ["订单", "物流", "快递"]):
        return "order_query"
    if "发票" in user_message:
        return "faq_query"
    if any(term in user_message for term in ["火星会员", "隐藏券", "不存在的活动", "未知活动"]):
        return "low_confidence_query"
    if any(term in user_message for term in ["活动", "满减", "会员券", "优惠券", "会员规则", "大促"]):
        if any(term in user_message for term in ["商品", "耳机", "音箱", "库存", "价格", "多少钱", "有货"]):
            return "product_query"
        return "promotion_query"
    if any(term in user_message for term in ["商品", "耳机", "音箱", "库存", "价格", "多少钱", "有货", "推荐"]):
        return "product_query"
    return "general_chat"


def classify_route_veto_intent(user_message: str, model_intent: Intent) -> Intent | None:
    """只否决被明确非动作上下文触发的高风险模型路由，不替代普通模型理解。"""
    if classify_guard_intent(user_message) is not None:
        return None

    relevant_terms: tuple[str, ...] = ()
    existing_request = False
    if model_intent == "refund_request":
        relevant_terms = ("退款", "退钱", "取消订单")
        existing_request = _is_existing_refund_request(user_message)
    elif model_intent == "return_request":
        relevant_terms = ("退货", "寄回", "七天无理由")
        existing_request = _is_existing_return_request(user_message)
    elif model_intent == "degradation_request":
        relevant_terms = ("SERVICE_TIMEOUT", "服务抽风", "工具超时", "接口不可用")
        existing_request = _is_explanation(user_message)
    elif model_intent == "security_request":
        relevant_terms = ("系统提示词", "hidden reasoning", "隐藏推理", "工具 schema", "内部策略")
    else:
        return None

    mentions_relevant_term = any(term in user_message for term in relevant_terms)
    if not mentions_relevant_term:
        return None
    if not existing_request and _contains_asserted_term(user_message, relevant_terms):
        return None

    fallback_intent = classify_intent(user_message)
    return fallback_intent if fallback_intent != model_intent else None


def extract_order_id(user_message: str) -> str | None:
    """从用户问题中抽取电商订单号，供工具调用前参数校验。"""
    match = _ORDER_ID_RE.search(user_message)
    return match.group(0) if match else None


def extract_return_reason(user_message: str) -> str | None:
    """只接受用户明确表达的退货原因，不由模型代填高风险售后事实。"""
    reason_terms = ("七天无理由", "质量问题", "商品破损", "发错货", "少件", "与描述不符")
    return next((term for term in reason_terms if term in user_message), None)


def route_tool_candidates() -> list[ToolCandidate]:
    """返回可暴露给路由模型的服务端工具目录，不把任意函数名交给模型猜测。"""
    return [
        ToolCandidate(
            name="get_order_detail",
            domain="order",
            risk_level="low",
            reason="读取当前用户订单事实，不执行业务写操作。",
        ),
        ToolCandidate(
            name="get_order_logistics",
            domain="logistics",
            risk_level="low",
            reason="读取当前用户订单及物流状态。",
        ),
        ToolCandidate(
            name="get_refund_status",
            domain="after_sale",
            risk_level="low",
            reason="只读查询当前用户订单的售后申请状态，不创建退款申请。",
        ),
        ToolCandidate(
            name="search_products",
            domain="product",
            risk_level="low",
            reason="查询商品价格、库存和活动等实时事实。",
        ),
    ]


def build_route_plan(
    *,
    intent: Intent,
    user_message: str,
    order_id: str | None,
    model_candidate: RoutePlanCandidate | None,
) -> RoutePlan:
    """把模型候选与服务端策略收敛成最终 RoutePlan；最终计划才有执行资格。"""
    candidate_catalog = {candidate.name: candidate for candidate in route_tool_candidates()}
    required_tools: list[str] = []
    knowledge_domains: list[str] = []
    risk_level: RiskLevel = "low"
    requires_workflow = False
    fallback_policy = "safe_deterministic_path"
    if intent == "order_query":
        required_tools = ["get_order_logistics"]
        fallback_policy = "tool_first"
    elif intent == "refund_status_query":
        required_tools = ["get_refund_status"]
        fallback_policy = "tool_first"
    elif intent == "refund_request":
        required_tools = ["get_order_detail"]
        knowledge_domains = ["after_sale_policy"]
        risk_level = "high"
        requires_workflow = True
        fallback_policy = "workflow_first"
    elif intent == "return_request":
        required_tools = ["get_order_detail"]
        knowledge_domains = ["received_return_policy"]
        risk_level = "high"
        requires_workflow = True
        fallback_policy = "workflow_first"
    elif intent == "product_query":
        required_tools = ["search_products"]
        knowledge_domains = ["promotion_and_member_policy"] if any(term in user_message for term in ["活动", "优惠", "满减", "会员"]) else []
        fallback_policy = "tool_first"
    elif intent in {"faq_query", "promotion_query", "low_confidence_query"}:
        knowledge_domains = ["faq"] if intent == "faq_query" else ["promotion_and_member_policy"]
        fallback_policy = "transfer_to_human" if intent == "low_confidence_query" else "knowledge_only"
    elif intent in {"security_request", "degradation_request"}:
        risk_level = "high" if intent == "security_request" else "medium"
        fallback_policy = "transfer_to_human"

    # 每类 intent 都有服务端许可范围。确定性基线只保留不可缺少的能力，
    # 模型可以在许可范围内补充组合路径，但不能发明工具、跨域或降低风险。
    allowed_tools_by_intent: dict[Intent, set[str]] = {
        "order_query": {"get_order_detail", "get_order_logistics"},
        "refund_status_query": {"get_refund_status"},
        "refund_request": {"get_order_detail"},
        "return_request": {"get_order_detail"},
        "product_query": {"search_products"},
    }
    from rag.domains import PUBLIC_DOMAINS, infer_public_domains
    allowed_domains_by_intent: dict[Intent, set[str]] = {
        "faq_query": set(PUBLIC_DOMAINS),
        "promotion_query": set(PUBLIC_DOMAINS),
        "low_confidence_query": set(PUBLIC_DOMAINS),
        "product_query": set(PUBLIC_DOMAINS),
        "order_query": set(PUBLIC_DOMAINS),
        "refund_request": {"after_sale_policy"},
        "return_request": {"received_return_policy"},
    }
    if intent in {"faq_query", "promotion_query", "low_confidence_query"}:
        knowledge_domains = sorted(set(knowledge_domains) | set(infer_public_domains(user_message)))
    candidate_applied = model_candidate is not None and (
        model_candidate.intent == intent or (
            intent in {"faq_query", "promotion_query"}
            and model_candidate.intent == "general_chat"
            and bool(model_candidate.knowledge_domains)
        )
    )
    policy_constraints = ["tool_allowlist", "knowledge_domain_allowlist", "risk_floor"]
    if candidate_applied:
        allowed_tools = allowed_tools_by_intent.get(intent, set())
        allowed_domains = allowed_domains_by_intent.get(intent, set())
        required_tools = list(
            dict.fromkeys(
                [
                    *required_tools,
                    *(name for name in model_candidate.required_tools if name in allowed_tools),
                ]
            )
        )
        knowledge_domains = list(
            dict.fromkeys(
                [
                    *knowledge_domains,
                    *(domain for domain in model_candidate.knowledge_domains if domain in allowed_domains),
                ]
            )
        )
        policy_constraints.insert(0, "structured_candidate_validated")
    if requires_workflow:
        policy_constraints.append("workflow_boundary")

    # 缺少订单号时保留候选工具，但不允许模型凭空生成参数并执行。
    order_bound_tools = {"get_order_detail", "get_order_logistics", "get_refund_status"}
    missing_required_entity = not order_id and any(name in order_bound_tools for name in required_tools)
    executable_tools = required_tools if not missing_required_entity else []
    if missing_required_entity:
        fallback_policy = "ask_order_id"
        policy_constraints.append("required_entity_gate")
    return RoutePlan(
        intent=intent,
        needs_rag=bool(knowledge_domains),
        needs_business_tools=bool(required_tools),
        required_tools=executable_tools,
        tool_candidates=[candidate_catalog[name] for name in required_tools],
        knowledge_domains=knowledge_domains,
        entity_refs=[order_id] if order_id else [],
        risk_level=risk_level,
        requires_workflow=requires_workflow,
        confidence=0.9 if candidate_applied else 0.75,
        source="llm_with_policy_constraints" if candidate_applied else "deterministic_fallback",
        fallback_policy=fallback_policy,
        policy_constraints=policy_constraints,
    )


def build_order_clarification(request: ChatRequest, route_plan: RoutePlan) -> ClarificationRequest | None:
    """后端根据 RoutePlan 必填参数和可信 Runtime Context 生成候选，不让模型代选订单。"""
    if route_plan.fallback_policy != "ask_order_id" or not route_plan.tool_candidates:
        return None
    orders = (request.runtime_context or {}).get("currentUserOrders", [])
    candidates: list[ClarificationCandidate] = []
    for order in orders:
        if str(order.get("userId") or request.runtime_user_id) != request.runtime_user_id:
            continue
        order_id = str(order.get("orderNo") or "").strip()
        if not order_id:
            continue
        items = order.get("items") or []
        product_names = "、".join(str(item.get("productName")) for item in items[:2] if item.get("productName"))
        candidates.append(
            ClarificationCandidate(
                value=order_id,
                label=order_id,
                hint=product_names or "当前账号订单",
            )
        )
    action = "退款" if route_plan.intent == "refund_request" else "查询"
    return ClarificationRequest(
        clarification_field="order_id",
        message=f"你要{action}哪一个订单？请选择订单号，或直接补充订单号。",
        candidates=candidates,
    )


def estimate_tokens(text: str) -> int:
    """用近似 token 估算服务成本治理和上下文预算展示。"""
    return max(1, len(text) // 2)
