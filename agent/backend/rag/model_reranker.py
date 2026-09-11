"""Query/document model reranking via the configured provider's /rerank API."""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from api.schemas import Citation
from config.settings import api_key_is_missing, load_course_env, openai_base_url


@dataclass
class RerankResult:
    citations: list[Citation]
    debug: dict[str, Any]


def rerank_citations(query: str, citations: list[Citation]) -> RerankResult:
    """Validate complete model results; errors preserve the original ranking.

    Scores are relevance scores, not calibrated answerability probabilities.
    Never expose credentials, provider response bodies or exception messages.
    """
    load_course_env()
    enabled = os.getenv("AGENT_RAG_RERANK_ENABLED", "false").lower() in {"1", "true", "yes"}
    model = os.getenv("AGENT_RAG_RERANK_MODEL", "Qwen/Qwen3-Reranker-8B")
    debug: dict[str, Any] = {
        "mode": "model_rerank", "enabled": enabled, "model_name": model,
        "used_model": False, "fallback_reason": None,
        "input_policy_ids": [(c.metadata or {}).get("policy_id") for c in citations],
        "policy_ids": [], "scores": {}, "reasons": {}, "latency_ms": 0,
    }
    def fallback(reason: str) -> RerankResult:
        debug["fallback_reason"] = reason
        debug["mode"] = "retrieval_order_fallback"
        return RerankResult(list(citations), debug)

    if not enabled:
        return fallback("disabled")
    if not citations:
        return fallback("no_candidates")
    base = os.getenv("AGENT_RAG_RERANK_BASE_URL", openai_base_url()).rstrip("/")
    key = os.getenv("AGENT_RAG_RERANK_API_KEY")
    if not key:
        # A separate provider must receive its own explicitly configured key.
        if urlsplit(base).netloc != urlsplit(openai_base_url()).netloc:
            return fallback("separate_provider_key_required")
        key = os.getenv("AGENT_OPENAI_API_KEY")
    if api_key_is_missing(key):
        return fallback("missing_api_key")
    started = time.perf_counter()
    try:
        threshold = float(os.getenv("AGENT_RAG_RERANK_MIN_SCORE", "0.5"))
        timeout = float(os.getenv("AGENT_RAG_RERANK_TIMEOUT_SECONDS", "15"))
        if not math.isfinite(threshold) or not 0 <= threshold <= 1 or not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("invalid rerank configuration")
        payload = {
            "model": model, "query": query,
            "documents": [c.snippet for c in citations],
            "top_n": len(citations), "return_documents": False,
        }
        # Only Qwen text rerankers support this provider parameter.
        if model.startswith("Qwen/Qwen3-Reranker-"):
            payload["instruction"] = (
                "Given a customer question, retrieve policy passages that directly support "
                "answering the question or one of its subquestions. Respect negation and "
                "distinguish topical similarity from evidence for the requested fact."
            )
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.post(base + "/rerank", json=payload,
                                   headers={"Authorization": f"Bearer {key}"})
            response.raise_for_status()
            data = response.json()
        results = data["results"]
        if not isinstance(results, list) or len(results) != len(citations):
            raise ValueError("incomplete rerank response")
        seen: set[int] = set()
        ranked: list[Citation] = []
        for item in results:
            index, score = item["index"], item["relevance_score"]
            if type(index) is not int or not 0 <= index < len(citations) or index in seen:
                raise ValueError("invalid document index")
            if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError("invalid relevance score")
            seen.add(index)
            source = citations[index]
            ranked.append(source.model_copy(update={
                "score": float(score),
                "metadata": {**(source.metadata or {}), "retrieval_score": source.score,
                             "rerank_score": float(score), "rerank_model": model},
            }))
        ranked.sort(key=lambda c: c.score, reverse=True)
        debug.update(used_model=True, min_score=threshold,
                     policy_ids=[(c.metadata or {}).get("policy_id") for c in ranked],
                     reasons={str((c.metadata or {}).get("policy_id")): ["query_document_model_score"] for c in ranked},
                     scores={str((c.metadata or {}).get("policy_id")): c.score for c in ranked})
        # Provider usage is separate from the existing chat-model cost summary.
        tokens = (data.get("meta") or {}).get("tokens") or data.get("usage") or {}
        debug["usage"] = {k: v for k, v in tokens.items()
                          if k in {"input_tokens", "output_tokens", "total_tokens", "prompt_tokens", "completion_tokens"}
                          and type(v) is int and v >= 0}
        return RerankResult(ranked, debug)
    except httpx.HTTPStatusError as exc:
        return fallback(f"http_{exc.response.status_code}")
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return fallback(type(exc).__name__)
    finally:
        debug["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)


def model_knowledge_result(session_id: str, query: str, retrieval, intent: str):
    """Return a model-ranked knowledge path, or None + trace for legacy fallback."""
    # Local import avoids the knowledge module's public result type import cycle.
    from rag.knowledge import KnowledgePathResult, low_confidence_result
    from safety.source_guard import inspect_source

    trusted = [c for c in retrieval.citations if not inspect_source("rag_document", c.snippet)["tainted"]]
    result = rerank_citations(query, trusted)
    debug = result.debug
    debug["source_guard_rejected_count"] = len(retrieval.citations) - len(trusted)
    event = ("rag_model_reranked", {"session_id": session_id, "intent": intent,
                                   "retrieval_stage": "pre_retrieval", **debug})
    if not debug["used_model"]:
        return None, event
    selected = [c for c in result.citations if c.score >= debug["min_score"]]
    debug["selected_policy_ids"] = [(c.metadata or {}).get("policy_id") for c in selected]
    debug["rejected_policy_ids"] = [(c.metadata or {}).get("policy_id") for c in result.citations if c not in selected]
    event[1].update(selected_policy_ids=debug["selected_policy_ids"], rejected_policy_ids=debug["rejected_policy_ids"])
    retrieval_debug = {**retrieval.debug, "model_rerank": debug}
    if not selected:
        fallback = low_confidence_result(session_id, intent)
        return KnowledgePathResult(
            answer=fallback.answer, citations=[], risk_level=fallback.risk_level,
            next_action=fallback.next_action, needs_human_approval=False,
            retrieval_debug=retrieval_debug, rerank=debug,
            trace_events=(event, *fallback.trace_events),
        ), event
    # Retain complementary evidence. Cached retrieval is safe to reuse, but a
    # policy ID alone is not a cache key for a question-specific final answer.
    return KnowledgePathResult(
        answer="\n".join(c.snippet.strip() for c in selected), citations=selected,
        risk_level="low", next_action="answer_user", needs_human_approval=False,
        cache_hit=False, rerank=debug, retrieval_debug=retrieval_debug,
        trace_events=(event, ("rag_pre_retrieved", {"session_id": session_id,
            "hit_count": len(selected), "retrieval_stage": "pre_retrieval",
            "candidate_policy_ids": debug["selected_policy_ids"]})),
    ), event
