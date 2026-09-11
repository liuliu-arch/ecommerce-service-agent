"""用户反馈归因层，把问题绑定到 Trace、Eval 和模块责任。"""

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
from state.session_state import BACKFILLED_CASES

class FailureAttributor:
    """把反馈、trace 和 eval 结果归因到具体模块。"""

    def attribute(
        self,
        *,
        feedback: FeedbackRequest,
        trace_events: list[TraceEvent],
        eval_result: EvalCaseResult | None,
    ) -> list[FailureAttribution]:
        """把用户反馈、Trace 和 Eval 失败类别映射到 Prompt、RAG、Tool、Context 或 Workflow。"""
        text = f"{feedback.user_comment} {feedback.observed_answer}"
        event_names = [event.event_type for event in trace_events]
        categories = eval_result.failure_categories if eval_result else []
        attributions: list[FailureAttribution] = []

        if any(term in text for term in ["已退款成功", "已到账", "直接退款", "不用审批", "跳过审批"]):
            attributions.append(
                FailureAttribution(
                    module="Workflow",
                    category="high_risk_boundary",
                    evidence=["反馈中出现高风险结果承诺", *[name for name in event_names if "workflow" in name or "approval" in name]],
                    suggested_fix="回到售后 workflow / HITL 边界，禁止 Prompt 直接承诺资金动作完成。",
                )
            )
            attributions.append(
                FailureAttribution(
                    module="Prompt",
                    category="overpromise",
                    evidence=["观察回答含已退款成功或已到账"],
                    suggested_fix="收紧客服回答边界：只能说明可提交申请或等待人工审批，不能承诺到账。",
                )
            )
        if "tool_path_mismatch" in categories or any(term in text for term in ["没查订单", "没查物流", "工具没调用"]):
            attributions.append(
                FailureAttribution(
                    module="Tool",
                    category="tool_path_mismatch",
                    evidence=["eval 报告显示工具路径不匹配"],
                    suggested_fix="检查意图路由、工具 schema 和工具调用前参数抽取。",
                )
            )
        if "citation_missing" in categories or any(term in text for term in ["没有依据", "引用错了", "政策不对"]):
            attributions.append(
                FailureAttribution(
                    module="RAG",
                    category="citation_or_retrieval",
                    evidence=["反馈指向依据缺失或引用错误"],
                    suggested_fix="检查检索 query、metadata、reranker 和 expected_citations。",
                )
            )
        if "session_state_mismatch" in categories or any(term in text for term in ["刚才那个", "VIP", "上下文", "串台"]):
            attributions.append(
                FailureAttribution(
                    module="Context",
                    category="context_boundary",
                    evidence=["反馈指向 Memory、Runtime Context 或上下文冲突"],
                    suggested_fix="检查 Context Builder 冲突规则、Runtime Context 权威性和 Memory 写入排除。",
                )
            )
        if "answer_signal_missing" in categories and not attributions:
            attributions.append(
                FailureAttribution(
                    module="EvaluationExpectation",
                    category="answer_expectation_gap",
                    evidence=["只有答案信号缺失，路径证据没有明显退化"],
                    suggested_fix="复核 case 期望是否过窄，再决定改 Prompt 还是调整测试表达。",
                )
            )
        if not attributions:
            attributions.append(
                FailureAttribution(
                    module="EvaluationExpectation",
                    category="needs_triage",
                    evidence=["反馈暂未命中明确模块规则"],
                    suggested_fix="先补充可复现 case，再通过 trace/eval 判断是 Prompt、RAG、Tool、Context 还是 Workflow。",
                )
            )
        return attributions


def build_backfilled_case(
    feedback: FeedbackRequest,
    attributions: list[FailureAttribution],
    base_case: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把一次负反馈沉淀成回归 case，让同类问题下次自动被测出来。"""
    case_id = f"feedback-{len(BACKFILLED_CASES) + 1:03d}"
    expected_trace_events = ["cost_recorded"]
    expected_session_state: list[str] = []
    forbidden_text: list[str] = []
    expected_signals = ["电商"]
    if any(item.module == "Workflow" for item in attributions):
        expected_signals = ["人工审批"]
        expected_trace_events.extend(["workflow_completed", "human_approval_required"])
        expected_session_state.append("workflow.pending_action=require_approval")
        forbidden_text.extend(["已退款成功", "已到账", "直接退款"])
    if any(item.module == "RAG" for item in attributions):
        expected_trace_events.append("rag_pre_retrieved")
    case = {
        "case_id": case_id,
        "user_message": feedback.user_comment,
        "expected_signals": expected_signals,
        "expected_trace_events": expected_trace_events,
        "expected_session_state": expected_session_state,
        "forbidden_text": forbidden_text,
        "source": "feedback_backfill",
    }
    if base_case and isinstance(base_case.get("runtime_context"), dict):
        case["runtime_context"] = base_case["runtime_context"]
    return case
