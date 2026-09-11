"""Pydantic 请求响应模型。第 41 课把所有公开 API 契约集中放在这里。"""

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
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

ReasoningView = Literal["default", "off", "summary", "teaching"]
Intent = Literal[
    "general_chat",
    "order_query",
    "refund_status_query",
    "refund_request",
    "return_request",
    "faq_query",
    "promotion_query",
    "product_query",
    "low_confidence_query",
    "degradation_request",
    "security_request",
    "unknown",
]
RiskLevel = Literal["low", "medium", "high"]
NextAction = Literal["answer_user", "ask_clarification", "transfer_to_human"]

CAPABILITIES_PATH = Path(__file__).with_name("agent_capabilities.json")
CASES_PATH = Path(__file__).with_name("cases.yml")
DEFAULT_COURSE_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
DEFAULT_ECOMMERCE_BASE_URL = "http://127.0.0.1:8081"
TRACE_SCHEMA_VERSION = "trace_event_v1"


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ToolCandidate(BaseModel):
    name: str
    domain: str
    risk_level: RiskLevel
    reason: str


class RoutePlanCandidate(BaseModel):
    """路由模型给出的结构化候选；它还不是可直接执行的最终计划。"""

    model_config = ConfigDict(extra="forbid", strict=True)

    intent: Intent
    needs_rag: StrictBool
    needs_business_tools: StrictBool
    required_tools: list[str] = Field(default_factory=list)
    knowledge_domains: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    requires_workflow: StrictBool
    fallback_policy: Literal[
        "safe_deterministic_path",
        "ask_order_id",
        "knowledge_only",
        "tool_first",
        "workflow_first",
        "transfer_to_human",
    ]

    @field_validator("required_tools", "knowledge_domains")
    @classmethod
    def validate_unique_non_empty_names(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("名称不能为空")
        if len(values) != len(set(values)):
            raise ValueError("名称不能重复")
        return values

    @model_validator(mode="after")
    def validate_cross_field_contract(self) -> "RoutePlanCandidate":
        if self.required_tools and not self.needs_business_tools:
            raise ValueError("required_tools 非空时 needs_business_tools 必须为 true")
        if self.knowledge_domains and not self.needs_rag:
            raise ValueError("knowledge_domains 非空时 needs_rag 必须为 true")
        if self.requires_workflow and self.risk_level != "high":
            raise ValueError("Workflow 候选必须标记为 high risk")
        if self.requires_workflow and self.fallback_policy != "workflow_first":
            raise ValueError("Workflow 候选必须使用 workflow_first")
        return self


class RoutePlan(BaseModel):
    """模型候选经过服务端业务策略收敛后的结构化执行计划。"""

    intent: Intent
    needs_rag: bool
    needs_business_tools: bool
    required_tools: list[str] = Field(default_factory=list)
    tool_candidates: list[ToolCandidate] = Field(default_factory=list)
    knowledge_domains: list[str] = Field(default_factory=list)
    entity_refs: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "low"
    requires_workflow: bool = False
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: Literal["llm_with_policy_constraints", "deterministic_fallback"]
    fallback_policy: str = "safe_deterministic_path"
    policy_constraints: list[str] = Field(default_factory=list)


class ClarificationCandidate(BaseModel):
    value: str
    label: str
    hint: str


class ClarificationRequest(BaseModel):
    """工具必填参数不足时，由后端校验并生成的结构化追问。"""

    clarification_field: str
    message: str
    candidates: list[ClarificationCandidate] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="当前对话会话 ID")
    runtime_user_id: str = Field(..., description="当前登录用户 ID，由调用方确认")
    runtime_nickname: str | None = Field(default=None, description="当前用户昵称")
    runtime_member_level: str | None = Field(default=None, description="当前会员等级，由调用方确认")
    runtime_risk_level: str | None = Field(default=None, description="当前账号风险等级，由调用方确认")
    user_message: str = Field(..., description="用户输入的问题")
    reasoning_view: ReasoningView = "default"
    debug: bool = True
    runtime_context: dict[str, Any] | None = None
    history_messages: list[HistoryMessage] = Field(default_factory=list)


class Citation(BaseModel):
    source: str
    title: str
    snippet: str
    score: float
    retrieval_stage: Literal["pre_retrieval", "tool_retrieval"] | None = None
    metadata: dict[str, Any] | None = None


class ToolCallTrace(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    output_summary: str
    status: Literal["success", "error"]
    tool_source: Literal["function", "mcp", "preload"] | None = "function"
    risk_level: RiskLevel | None = None
    needs_human_approval: bool | None = None
    next_action: str | None = None
    error_type: str | None = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    clarification_field: str | None = None
    clarification_prompt: str | None = None


class TraceEvent(BaseModel):
    event_type: str
    timestamp: datetime
    agent_mode: str | None = None
    step: int | None = None
    schema_version: str
    category: str
    stage: str
    name: str
    status: str
    target: dict[str, Any]
    ids: dict[str, Any]
    summary: dict[str, Any]
    signals: list[str]
    safety: dict[str, Any]
    payload: dict[str, Any]


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    tool_calls: list[ToolCallTrace]
    clarification: ClarificationRequest | None = None
    reasoning_summary: list[str]
    reasoning_content: str | None = None
    session_state: dict[str, Any]


class EvalRunRequest(BaseModel):
    case_id: str | None = None


class EvalCaseResult(BaseModel):
    case_id: str
    passed: bool
    user_message: str
    expected_signals: list[str]
    actual_answer: str
    actual_tools: list[str]
    missing_signals: list[str]
    actual_citations: list[str] = []
    actual_trace_events: list[str] = []
    missing_tools: list[str] = []
    unexpected_tools: list[str] = []
    missing_citations: list[str] = []
    forbidden_citation_hits: list[str] = []
    missing_trace_events: list[str] = []
    missing_session_state: list[str] = []
    forbidden_text_hits: list[str] = []
    failure_categories: list[str] = []


class EvalRunResponse(BaseModel):
    total: int
    passed: int
    failed: int
    summary: dict[str, Any]
    results: list[EvalCaseResult]


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., description="发生反馈的会话 ID")
    case_id: str | None = Field(default=None, description="如果这次事故能对应已有 eval case，就绑定它")
    rating: Literal["negative", "neutral", "positive"] = "negative"
    user_comment: str
    observed_answer: str


class FailureAttribution(BaseModel):
    module: Literal["Prompt", "RAG", "Tool", "Context", "Workflow", "EvaluationExpectation"]
    category: str
    evidence: list[str]
    suggested_fix: str


class FeedbackRecord(BaseModel):
    feedback_id: str
    session_id: str
    case_id: str | None
    rating: str
    user_comment: str
    trace_event_names: list[str]
    eval_failure_categories: list[str]
    attributions: list[FailureAttribution]
    backfilled_case: dict[str, Any]


class FeedbackSubmitResponse(BaseModel):
    record: FeedbackRecord
    eval_report: EvalRunResponse | None = None


class ChatResumeRequest(BaseModel):
    session_id: str = Field(..., description="要恢复的会话 ID")
    workflow_id: str = Field(..., description="待恢复 workflow ID")
    resume_token: str = Field(..., description="暂停时返回的恢复令牌")
    reviewer_id: str = Field(..., description="审批人 ID")
    reviewer_role: str = Field(..., description="审批人角色")
    decision: Literal["approved", "rejected", "needs_more_info"]
    reviewer_note: str | None = None


class ChatResumeResponse(BaseModel):
    session_id: str
    workflow_id: str
    status: Literal["completed", "paused", "rejected", "blocked"]
    answer: str
    resume_result: dict[str, Any]
    workflow: dict[str, Any] | None
    business_recheck: dict[str, Any]
    session_state: dict[str, Any]
