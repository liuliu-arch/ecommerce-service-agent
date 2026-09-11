"""课程内置知识片段。总演习把售后、发票、活动和会员规则集中成可引用 Citation。"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Any

from api.schemas import *
from course_runtime.course_logging import log_course_event
from rag.documents import load_knowledge_citation
from rag.hybrid_retrieval import normalize_query, retrieve_knowledge
from safety.source_guard import inspect_source
from state.session_state import COMMON_HIT_CACHE

REFUND_POLICY = load_knowledge_citation("after_sale_policy.md")
RETURN_POLICY = load_knowledge_citation("received_return_policy.md")
INVOICE_FAQ = load_knowledge_citation("payment_invoice_policy.md")
PROMOTION_POLICY = load_knowledge_citation("promotion_policy.md")
MEMBER_COUPON_POLICY = load_knowledge_citation("member_coupon_policy.md")
FAQ_MIN_EVIDENCE_SCORE = 0.34


@dataclass(frozen=True)
class KnowledgePathResult:
    """稳定知识路径的确定性结果，供 Agent 编排层直接拼装响应。"""

    answer: str
    citations: list[Citation]
    risk_level: RiskLevel
    next_action: NextAction
    needs_human_approval: bool
    cache_hit: bool = False
    cache_key: str | None = None
    rerank: dict[str, Any] | None = None
    retrieval_debug: dict[str, Any] | None = None
    trace_events: tuple[tuple[str, dict[str, Any]], ...] = ()


def low_confidence_result(session_id: str, intent: Intent) -> KnowledgePathResult:
    """纯知识低置信场景保守兜底，不让模型编造隐藏规则。"""
    answer = (
        "没有检索到电商公司已发布且与当前问题充分匹配的可信 FAQ，我不能用相似但无关的知识代替答案。建议补充具体问题，或转人工客服进一步核实。"
        if intent == "faq_query"
        else "没有检索到电商公司已发布的可信活动或会员规则，我不能编造隐藏券规则。建议以活动页和结算页展示为准，或转人工客服进一步核实。"
    )
    log_course_event(
        "RAG_LOW_CONFIDENCE",
        "可信证据不足，RAG 已停止生成并转入保守兜底",
        teaching=True,
        intent=intent,
        evidence_count=0,
        next_action="transfer_to_human",
    )
    return KnowledgePathResult(
        answer=answer,
        citations=[],
        risk_level="medium",
        next_action="transfer_to_human",
        needs_human_approval=False,
        trace_events=(
            (
                "rag_low_confidence_fallback",
                {
                    "session_id": session_id,
                    "intent": intent,
                    "hit_count": 0,
                    "retrieval_stage": "pre_retrieval",
                    "pending_action": "transfer_to_human",
                    "status": "low_confidence",
                },
            ),
        ),
    )


def _legacy_faq_knowledge_result(session_id: str, user_message: str) -> KnowledgePathResult:
    """按真实问题选择 FAQ 证据；公共缓存只保存通过证据门的知识答案。"""
    retrieval = retrieve_knowledge(user_message, "faq_query")
    citation = next(
        (
            item
            for item in retrieval.citations
            if (item.metadata or {}).get("knowledge_domain") == "faq"
            and item.score >= FAQ_MIN_EVIDENCE_SCORE
        ),
        None,
    )
    if citation is None:
        log_course_event(
            "RAG_EVIDENCE_GATE",
            "FAQ 候选未通过最低证据分数门",
            teaching=True,
            accepted=False,
            threshold=FAQ_MIN_EVIDENCE_SCORE,
            candidates=[
                {"policy_id": (item.metadata or {}).get("policy_id"), "score": item.score}
                for item in retrieval.citations
            ],
        )
        fallback = low_confidence_result(session_id, "faq_query")
        return KnowledgePathResult(
            answer=fallback.answer,
            citations=[],
            risk_level=fallback.risk_level,
            next_action=fallback.next_action,
            needs_human_approval=fallback.needs_human_approval,
            retrieval_debug={
                **retrieval.debug,
                "faq_selection": {
                    "accepted": False,
                    "reason": "no_candidate_passed_evidence_gate",
                    "threshold": FAQ_MIN_EVIDENCE_SCORE,
                    "selected_policy_id": None,
                },
            },
            trace_events=fallback.trace_events,
        )

    metadata = citation.metadata or {}
    policy_id = str(metadata["policy_id"])
    index_version = str(retrieval.debug["index_version"])
    cache_key = f"faq:{index_version}:{policy_id}"
    source_report = inspect_source("rag_document", citation.snippet)
    if source_report["tainted"]:
        log_course_event(
            "RAG_SOURCE_GUARD",
            "候选知识包含不可信指令，已在进入 Prompt 前拒绝",
            teaching=True,
            policy_id=policy_id,
            source=citation.source,
            guard_reason=source_report.get("reason"),
        )
        fallback = low_confidence_result(session_id, "faq_query")
        return KnowledgePathResult(
            answer=fallback.answer,
            citations=[],
            risk_level=fallback.risk_level,
            next_action=fallback.next_action,
            needs_human_approval=fallback.needs_human_approval,
            retrieval_debug={
                **retrieval.debug,
                "faq_selection": {
                    "accepted": False,
                    "reason": "tainted_knowledge_rejected",
                    "threshold": FAQ_MIN_EVIDENCE_SCORE,
                    "selected_policy_id": policy_id,
                },
            },
            trace_events=fallback.trace_events,
        )
    selection_debug = {
        **retrieval.debug,
        "faq_selection": {
            "accepted": True,
            "reason": "top_ranked_candidate_passed_evidence_gate",
            "threshold": FAQ_MIN_EVIDENCE_SCORE,
            "selected_policy_id": policy_id,
            "selected_score": citation.score,
            "knowledge_version": metadata.get("knowledge_version"),
            "cache_key": cache_key,
        },
    }
    log_course_event(
        "RAG_EVIDENCE_GATE",
        "FAQ 头部候选已通过证据门",
        teaching=True,
        accepted=True,
        threshold=FAQ_MIN_EVIDENCE_SCORE,
        selected_policy_id=policy_id,
        selected_score=citation.score,
        knowledge_version=metadata.get("knowledge_version"),
    )
    cached = COMMON_HIT_CACHE.get(cache_key)
    if cached:
        log_course_event(
            "RAG_ANSWER_CACHE_HIT",
            "已命中经过证据校验的公共知识答案缓存",
            teaching=True,
            cache_key=cache_key,
            policy_id=policy_id,
            cache_scope=metadata.get("cache_scope") or "public_shared",
        )
        return KnowledgePathResult(
            answer=str(cached["answer"]),
            citations=[Citation.model_validate(cached["citation"])],
            risk_level="low",
            next_action="answer_user",
            needs_human_approval=False,
            cache_hit=True,
            cache_key=cache_key,
            retrieval_debug=selection_debug,
        )

    answer = citation.snippet.strip()
    # policy_id 与索引版本共同确定公共知识；模型话术和 Runtime Context 永不进入缓存。
    COMMON_HIT_CACHE[cache_key] = {
        "answer": answer,
        "citation": citation.model_dump(),
        "policy_id": policy_id,
        "knowledge_version": str(metadata.get("knowledge_version") or index_version),
        "query_fingerprint": hashlib.sha256(normalize_query(user_message).encode("utf-8")).hexdigest()[:12],
        "source": "verified_knowledge_answer",
        "scope": str(metadata.get("cache_scope") or "public_shared"),
    }
    log_course_event(
        "RAG_ANSWER_CACHE_WRITE",
        "可信知识答案已写入公共缓存，Runtime Context 不进入缓存",
        teaching=True,
        cache_key=cache_key,
        policy_id=policy_id,
        knowledge_version=metadata.get("knowledge_version"),
        cache_scope=metadata.get("cache_scope") or "public_shared",
    )
    return KnowledgePathResult(
        answer=answer,
        citations=[citation],
        risk_level="low",
        next_action="answer_user",
        needs_human_approval=False,
        cache_key=cache_key,
        retrieval_debug=selection_debug,
        trace_events=(
            (
                "rag_pre_retrieved",
                {
                    "session_id": session_id,
                    "hit_count": 1,
                    "retrieval_stage": "pre_retrieval",
                    "policy_id": policy_id,
                    "score": citation.score,
                    "knowledge_version": metadata.get("knowledge_version"),
                },
            ),
        ),
    )


def _legacy_promotion_policy_result(session_id: str, user_message: str) -> KnowledgePathResult:
    """活动和会员券问题先过证据门，再用课程版 reranker 决定最终引用顺序。"""
    normalized = user_message.replace(" ", "").lower()
    if any(term in normalized for term in ("隐藏券", "火星会员", "不存在的活动", "未知活动", "未发布")):
        candidates: list[tuple[Citation, float, list[str]]] = []
        retrieval_debug = {"mode": "evidence_gate_blocked_before_retrieval", "reason": "unsupported_policy_claim"}
        log_course_event(
            "RAG_EVIDENCE_GATE",
            "问题要求未发布规则，证据门已在检索前阻断",
            teaching=True,
            accepted=False,
            reason="unsupported_policy_claim",
        )
    else:
        retrieval = retrieve_knowledge(user_message, "promotion_query")
        retrieval_debug = retrieval.debug
        allowed_policy_ids = _promotion_scope_policy_ids(normalized)
        candidates = [
            (
                citation,
                citation.score,
                list(
                    retrieval.debug.get("source_scores", {})
                    .get((citation.metadata or {}).get("policy_id"), {})
                    .get("sources", [])
                ),
            )
            for citation in retrieval.citations
            if (citation.metadata or {}).get("policy_id") in allowed_policy_ids
        ]
        if "叠加" in normalized and len(candidates) < 2:
            candidates = []
        log_course_event(
            "RAG_SCOPE_FILTERED",
            "召回候选已按当前活动问题的规则范围过滤",
            teaching=True,
            allowed_policy_ids=sorted(allowed_policy_ids),
            candidates=[
                {"policy_id": (citation.metadata or {}).get("policy_id"), "score": score, "recall_sources": reasons}
                for citation, score, reasons in candidates
            ],
        )
    reranked = _rerank_promotion_candidates(user_message, candidates)
    citations = [citation for citation, _score, _reasons in reranked]
    if not citations:
        result = low_confidence_result(session_id, "promotion_query")
        return KnowledgePathResult(
            answer=result.answer,
            citations=result.citations,
            risk_level=result.risk_level,
            next_action=result.next_action,
            needs_human_approval=result.needs_human_approval,
            retrieval_debug=retrieval_debug,
            trace_events=(
                (
                    "rag_evidence_gate_blocked",
                    {
                        "session_id": session_id,
                        "intent": "promotion_query",
                        "hit_count": 0,
                        "retrieval_stage": "pre_retrieval",
                        "status": "low_confidence",
                        "reason": "no_trusted_policy_citation",
                    },
                ),
                *result.trace_events,
            ),
        )
    rerank_debug = _build_rerank_debug(reranked)
    rerank_debug["retrieval"] = retrieval_debug
    log_course_event(
        "RAG_RERANKED",
        "候选已按当前问题的业务约束重新排序，引用顺序随之确定",
        teaching=True,
        mode=rerank_debug["mode"],
        policy_ids=rerank_debug["policy_ids"],
        scores=rerank_debug["scores"],
        reasons=rerank_debug["reasons"],
    )
    return KnowledgePathResult(
        answer=_promotion_policy_answer(citations),
        citations=citations,
        risk_level="low",
        next_action="answer_user",
        needs_human_approval=False,
        rerank=rerank_debug,
        retrieval_debug=retrieval_debug,
        trace_events=(
            (
                "rag_pre_retrieved",
                {
                    "session_id": session_id,
                    "hit_count": len(citations),
                    "retrieval_stage": "pre_retrieval",
                    "policy_id": "promotion_618_stack_rule",
                    "candidate_policy_ids": [
                        citation.metadata.get("policy_id") for citation, _score, _reasons in candidates if citation.metadata
                    ],
                },
            ),
            (
                "rag_reranked",
                {
                    "session_id": session_id,
                    "mode": rerank_debug["mode"],
                    "reranked_policy_ids": rerank_debug["policy_ids"],
                    "top_policy_id": rerank_debug["policy_ids"][0] if rerank_debug["policy_ids"] else None,
                    "rerank_reasons": rerank_debug["reasons"],
                },
            ),
        ),
    )


def _promotion_scope_policy_ids(normalized_query: str) -> set[str]:
    """单一问题只引用对应规则；明确问叠加时才联合两类证据。"""
    asks_promotion = any(term in normalized_query for term in ("618", "大促", "活动", "满减", "300减40"))
    asks_member = any(term in normalized_query for term in ("会员", "会员券", "金卡", "优惠券"))
    if asks_promotion and not asks_member:
        return {"promotion_618_stack_rule"}
    if asks_member and not asks_promotion:
        return {"member_coupon_gold_rule"}
    return {"promotion_618_stack_rule", "member_coupon_gold_rule"}


def _rerank_promotion_candidates(
    user_message: str,
    candidates: list[tuple[Citation, float, list[str]]],
) -> list[tuple[Citation, float, list[str]]]:
    """课程版轻量 reranker：在候选池里按当前问题的业务约束重新排序。

    这里刻意不调用外部商业模型，避免第 41 课总演习依赖网络；但保留 reranker 的核心闭环：
    初召回候选、按问题重排、citation 跟随最终排序。
    """
    normalized = user_message.replace(" ", "").lower()
    reranked: list[tuple[Citation, float, list[str]]] = []
    for citation, score, reasons in candidates:
        policy_id = citation.metadata.get("policy_id") if citation.metadata else ""
        final_score = score
        final_reasons = list(reasons)
        if policy_id == "promotion_618_stack_rule" and any(term in normalized for term in ("618", "满减", "300减40", "大促")):
            final_score += 0.18
            final_reasons.append("当前大促规则加权")
        if policy_id == "member_coupon_gold_rule" and any(term in normalized for term in ("金卡", "会员券")):
            final_score += 0.16
            final_reasons.append("会员券条件匹配")
        if "叠加" in normalized:
            final_score += 0.08
            final_reasons.append("叠加问题需要联合引用")
        reranked.append((citation, round(min(1.0, final_score), 3), final_reasons))
    return sorted(reranked, key=lambda item: item[1], reverse=True)


def _build_rerank_debug(reranked: list[tuple[Citation, float, list[str]]]) -> dict[str, Any]:
    """把 rerank 结果压成公开调试状态，方便第 41 课观察最终闭环。"""
    policy_ids = [citation.metadata.get("policy_id") for citation, _score, _reasons in reranked if citation.metadata]
    return {
        "mode": "lesson41_lightweight",
        "policy_ids": policy_ids,
        "scores": {citation.metadata.get("policy_id"): score for citation, score, _reasons in reranked if citation.metadata},
        "reasons": {citation.metadata.get("policy_id"): reasons for citation, _score, reasons in reranked if citation.metadata},
    }


def _promotion_policy_answer(citations: list[Citation]) -> str:
    """按实际命中的 citation 组织回答，避免单一证据问题被迫套完整叠加规则。"""
    policy_ids = {citation.metadata.get("policy_id") for citation in citations if citation.metadata}
    if {"promotion_618_stack_rule", "member_coupon_gold_rule"}.issubset(policy_ids):
        return (
            "根据电商公司 618 大促规则，满 300 减 40 可以与平台会员券叠加，"
            "但不能与同类型满减券重复叠加；金卡会员券需要在有效期内由本人账号使用。"
        )
    if "promotion_618_stack_rule" in policy_ids:
        return "根据电商公司 618 大促规则，满 300 减 40 活动可用，但不能与同类型满减券重复叠加。"
    if "member_coupon_gold_rule" in policy_ids:
        return "根据电商公司会员券使用规则，金卡会员可领取平台会员券；会员券需在有效期内由本人账号使用，不能转让。"
    return "没有检索到电商公司已发布的可信活动或会员规则，我不能编造隐藏券规则。建议以活动页和结算页展示为准，或转人工客服进一步核实。"


def _ranked_knowledge_result(session_id: str, user_message: str, intent: Intent, legacy) -> KnowledgePathResult:
    from rag.model_reranker import model_knowledge_result

    retrieval = retrieve_knowledge(user_message, intent)
    result, event = model_knowledge_result(session_id, user_message, retrieval, intent)
    if result is not None:
        return result
    fallback = legacy(session_id, user_message)
    return replace(fallback,
                   retrieval_debug={**(fallback.retrieval_debug or {}), "model_rerank": event[1]},
                   trace_events=(event, *fallback.trace_events))


def faq_knowledge_result(session_id: str, user_message: str, knowledge_domains=None) -> KnowledgePathResult:
    from rag.grounded_pipeline import grounded_knowledge_result
    return grounded_knowledge_result(session_id, user_message, "faq_query", knowledge_domains)


def promotion_policy_result(session_id: str, user_message: str, knowledge_domains=None) -> KnowledgePathResult:
    from rag.grounded_pipeline import grounded_knowledge_result
    return grounded_knowledge_result(session_id, user_message, "promotion_query", knowledge_domains)
