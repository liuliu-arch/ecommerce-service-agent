"""成本治理层，集中计算请求路径、Prompt 片段、Observation 压缩和预算信号。"""

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
from tools.planning import estimate_tokens


def observation_compression(tool_calls: list[ToolCallTrace]) -> dict[str, Any]:
    """压缩工具 Observation 摘要，保留状态、风险和下一步，减少上下文成本。"""
    original_tokens = sum(estimate_tokens(call.output_summary) for call in tool_calls)
    # Observation 进入模型前只保留状态、下一步和风险摘要，不把工具原始结果整段塞回去。
    compressed_tokens = sum(min(12, estimate_tokens(call.output_summary)) for call in tool_calls)
    return {
        "schema_version": "observation_compression_v1",
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "saved_tokens": max(0, original_tokens - compressed_tokens),
        "strategy": "keep_status_next_action_and_risk_summary",
    }


def build_cost_summary(
    *,
    request: ChatRequest,
    intent: Intent,
    tool_calls: list[ToolCallTrace],
    citations: list[Citation],
    workflow: dict[str, Any] | None,
    answer: str,
    cache_hit: bool,
    common_cache_key: str | None = None,
    route_model_used: bool = False,
    answer_model_used: bool = False,
    reasoning_content_returned: bool = False,
    reasoning_source: str | None = None,
    degraded: bool = False,
    degradation_reason: str | None = None,
    prompt_fragments: list[dict[str, Any]] | None = None,
    tool_agent_model_calls: int = 0,
    rag_debug: dict[str, Any] | None = None,
    answer_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """生成请求级成本摘要，把模型、RAG、工具、缓存、workflow 和预算信号集中呈现。"""
    rag_debug = rag_debug or {}
    checks = [*rag_debug.get("grounding_model_calls", []), *([answer_validation] if answer_validation else [])]
    has_workflow = bool(workflow)
    used_langgraph = bool(workflow and workflow.get("used_langgraph"))
    path_type = "cached_faq_light_path" if cache_hit else "langgraph_after_sale_workflow" if used_langgraph else "light_react_agent"
    fragments = prompt_fragments or []
    context_tokens = estimate_tokens(request.user_message) + sum(estimate_tokens(call.output_summary) for call in tool_calls)
    prompt_tokens = sum(int(fragment.get("estimated_tokens", 0)) for fragment in fragments)
    answer_tokens = estimate_tokens(answer)
    if cache_hit:
        prompt_tokens = max(8, prompt_tokens // 3)
        answer_tokens = max(4, answer_tokens // 2)
    total_tokens = context_tokens + prompt_tokens + answer_tokens
    compressed = observation_compression(tool_calls)
    warnings: list[str] = []
    if total_tokens > 160:
        warnings.append("total_estimated_tokens_over_teaching_budget")
    if len(tool_calls) > 3:
        warnings.append("tool_call_count_high")
    return {
        "schema_version": "cost_summary_v1",
        "cost_profile": "teaching",
        "path_type": path_type,
        "model_calls": {
            "route_planner": 1 if route_model_used else 0,
            "tool_agent": tool_agent_model_calls,
            "final_answer": 1 if answer_model_used else 0,
            "extra_reasoning": 0,
            "answerability": sum(int(c.get("attempted", False)) for c in rag_debug.get("grounding_model_calls", [])),
            "answer_validation": int(bool((answer_validation or {}).get("attempted"))),
            "rerank": rag_debug.get("rerank_model_calls", 0),
        },
        "frameworks": {
            "langchain_runnable_sequence": route_model_used or answer_model_used,
            "langchain_create_agent": tool_agent_model_calls > 0,
            "langgraph_state_graph": used_langgraph,
            "offline_deterministic_fallback": not (route_model_used or answer_model_used or used_langgraph),
        },
        "tool_call_count": len(tool_calls),
        "business_tool_call_count": sum(1 for call in tool_calls if call.tool_name != "retrieve_knowledge"),
        "rag": {
            "needs_rag": bool(citations),
            "hit_count": len(citations),
            "pre_retrieval_count": rag_debug.get("pre_retrieval_count", 0 if cache_hit else (1 if citations else 0)),
            "tool_retrieval_count": rag_debug.get("secondary_retrieval_count", 0),
            "retrieval_paths": [citation.retrieval_stage for citation in citations if citation.retrieval_stage],
            "cache_hit": cache_hit,
        },
        "grounding_usage": {"scope": "answerability_and_validation_only", "calls": checks,
                            "total_reported_tokens": sum(c.get("usage", {}).get("total_tokens", 0) for c in checks)},
        "tokens": {
            "context_estimated": context_tokens,
            "prompt_estimated": prompt_tokens,
            "answer_estimated": answer_tokens,
            "total_estimated": total_tokens,
            "context_budget": 160,
        },
        "prompt_fragments": {
            "selected": [str(fragment.get("name")) for fragment in fragments],
            "selections": fragments,
            "fragment_count": len(fragments),
            "fragmentized": bool(fragments),
            "source": "actual_model_invocations",
        },
        "cache": {
            "common_hit_cache": cache_hit,
            "cache_key": common_cache_key,
            "does_not_cache_high_risk_workflow": True,
        },
        "observation_compression": compressed,
        "workflow": {
            "used_langgraph": used_langgraph,
            "workflow_id": workflow.get("workflow_id") if workflow else None,
            "workflow_type": workflow.get("workflow_type") if workflow else None,
            "graph_name": workflow.get("graph_name") if workflow else None,
            "node_history": workflow.get("node_history", []) if workflow else [],
            "hitl_required": bool(workflow and workflow.get("pending_action") == "require_approval"),
            "status": workflow.get("status") if workflow else None,
        },
        "degradation": {
            "degraded": degraded,
            "reason": degradation_reason,
            "cost_threshold_exceeded": bool(warnings),
            "warnings": warnings,
        },
        "reasoning": {
            "view": request.reasoning_view,
            "thinking_requested": request.reasoning_view == "teaching",
            "reasoning_content_returned": reasoning_content_returned,
            "source": reasoning_source,
        },
        "safety_boundary": {
            "cost_control_does_not_skip_business_facts": True,
            "cost_control_does_not_skip_hitl": True,
            "not_finops_or_billing_system": True,
        },
    }
