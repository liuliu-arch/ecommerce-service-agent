"""第 41 课：基于受控事实生成最终客服回复的真实模型客户端。"""

from __future__ import annotations

from course_runtime.course_logging import log_model_input, log_model_output

import json
import os
from typing import Any

from pydantic import BaseModel, Field

from api.schemas import ChatRequest, Citation, Intent, ToolCallTrace
from config.settings import api_key_is_missing, load_course_env, openai_base_url, openai_model_name
from prompts.loader import PromptManager, prompt_manager


class FinalAnswerModelResult(BaseModel):
    """模型生成最终回复的结果。"""

    answer: str
    used_model: bool = False
    model_name: str | None = None
    fallback_reason: str | None = None
    reasoning_content: str | None = None
    reasoning_source: str | None = None
    framework: str | None = None
    prompt_fragments: list[dict[str, Any]] = Field(default_factory=list)
    validation: dict[str, Any] | None = None


class ModelInvocationResult(BaseModel):
    """保留一次主链路模型调用中的回复文本和可选 reasoning_content。"""

    content: str
    reasoning_content: str | None = None


class FinalAnswerModelClient:
    """只负责把受控上下文交给真实模型生成客服话术。"""

    def __init__(self, manager: PromptManager = prompt_manager) -> None:
        self.prompt_manager = manager

    def can_call_model(self) -> bool:
        """检查当前课程环境是否能真实调用聊天模型。"""
        load_course_env()
        if os.getenv("AGENT_COURSE_DISABLE_LLM") == "1":
            return False
        if api_key_is_missing(os.getenv("AGENT_OPENAI_API_KEY")):
            return False
        try:
            self._chat_model_class()
        except ImportError:
            return False
        return True

    def compose_answer(
        self,
        *,
        request: ChatRequest,
        intent: Intent,
        deterministic_answer: str,
        risk_level: str,
        next_action: str,
        tool_calls: list[ToolCallTrace],
        citations: list[Citation],
        workflow: dict[str, Any] | None,
        enable_reasoning: bool = False,
        model_context: list[str] | None = None,
    ) -> FinalAnswerModelResult:
        """基于已验证事实生成最终客服话术，不能新增业务事实或越过审批边界。"""
        if not self.can_call_model():
            return FinalAnswerModelResult(answer=deterministic_answer, fallback_reason="model_config_missing")
        try:
            prompt_signals = {
                "phase": "final_answer",
                "needs_business_tools": bool(tool_calls),
                "needs_rag": bool(citations),
                "high_risk_after_sale": bool(workflow) or risk_level == "high",
            }
            fragments = self.prompt_manager.select_fragments(prompt_signals)
            system_prompt = self.prompt_manager.render_system_prompt(fragments)
            prompt_fragments = self.prompt_manager.selection_summary(fragments, phase="final_answer")
            payload = {
                "user_message": request.user_message,
                "intent": intent,
                "runtime_context": {
                    "runtime_user_id": request.runtime_user_id,
                    "nickname": request.runtime_nickname or "unknown",
                    "member_level": request.runtime_member_level or "unknown",
                    "risk_level": request.runtime_risk_level or "unknown",
                },
                "risk_level": risk_level,
                "next_action": next_action,
                "tool_observations": [
                    {
                        "tool_name": call.tool_name,
                        "status": call.status,
                        "output_summary": call.output_summary,
                        "risk_level": call.risk_level,
                        "next_action": call.next_action,
                    }
                    for call in tool_calls
                ],
                "citations": [
                    {
                        "source": citation.source,
                        "title": citation.title,
                        "snippet": citation.snippet,
                        "policy_id": (citation.metadata or {}).get("policy_id"),
                    }
                    for citation in citations
                ],
                "workflow": self._public_workflow(workflow),
                "context_builder": model_context or [],
                "fallback_answer": deterministic_answer,
            }
            payload_text = json.dumps(payload, ensure_ascii=False)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload_text},
            ]
            log_model_input(model=openai_model_name(), messages=messages, prompt_source=__file__)
            if enable_reasoning:
                invocation = self._invoke_openai_model(messages, temperature=0.2, enable_thinking=True)
                framework = "openai_compatible_reasoning_api"
            else:
                model = self._create_chat_model(temperature=0.2, enable_thinking=False)
                invocation = self._invoke_chain(model, payload_text, system_prompt)
                framework = "langchain_runnable_sequence"
            content = invocation.content.strip()
            log_model_output(model=openai_model_name(), content=content)
            if not content:
                return FinalAnswerModelResult(
                    answer=deterministic_answer,
                    model_name=openai_model_name(),
                    fallback_reason="empty_model_answer",
                    prompt_fragments=prompt_fragments,
                )
            validation = None
            if citations or tool_calls:
                from rag.grounding import validate_answer
                content, validation = validate_answer(request.user_message, content, deterministic_answer, citations, tool_calls, trusted_identity=payload["runtime_context"])
            return FinalAnswerModelResult(
                answer=content,
                validation=validation,
                fallback_reason="answer_grounding_rejected" if validation and not validation["accepted"] else None,
                used_model=True,
                model_name=openai_model_name(),
                reasoning_content=invocation.reasoning_content if enable_reasoning else None,
                reasoning_source="main_final_answer_model" if enable_reasoning and invocation.reasoning_content else None,
                framework=framework,
                prompt_fragments=prompt_fragments,
            )
        except Exception as exc:
            return FinalAnswerModelResult(
                answer=deterministic_answer,
                model_name=openai_model_name(),
                fallback_reason=exc.__class__.__name__,
            )

    @staticmethod
    def _public_workflow(workflow: dict[str, Any] | None) -> dict[str, Any] | None:
        if workflow is None:
            return None
        return {
            "workflow_id": workflow.get("workflow_id"),
            "workflow_type": workflow.get("workflow_type"),
            "status": workflow.get("status"),
            "pending_action": workflow.get("pending_action"),
            "order_id": workflow.get("order_id"),
            "resume_token": workflow.get("resume_token"),
        }

    @staticmethod
    def _chat_model_class() -> Any:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI

    def _create_chat_model(self, *, temperature: float, enable_thinking: bool = False) -> Any:
        load_course_env()
        chat_model_class = self._chat_model_class()
        extra_body = None
        if "siliconflow.cn" in openai_base_url():
            extra_body = {"enable_thinking": enable_thinking}
            if enable_thinking:
                extra_body["thinking_budget"] = 512
        return chat_model_class(
            model=openai_model_name(),
            api_key=os.getenv("AGENT_OPENAI_API_KEY"),
            base_url=openai_base_url(),
            temperature=temperature,
            extra_body=extra_body,
            timeout=45,
            max_retries=0,
        )

    @staticmethod
    def _invoke_chain(model: Any, payload_text: str, system_prompt: str) -> ModelInvocationResult:
        """用 LangChain RunnableSequence 组合可替换 Prompt、模型和文本解析器。"""
        from langchain_core.messages import SystemMessage
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                ("human", "{controlled_payload}"),
            ]
        )
        chain = prompt | model | StrOutputParser()
        return ModelInvocationResult(content=str(chain.invoke({"controlled_payload": payload_text})))

    @staticmethod
    def _invoke_openai_model(
        messages: list[dict[str, str]],
        *,
        temperature: float,
        enable_thinking: bool,
    ) -> ModelInvocationResult:
        from openai import OpenAI

        extra_body = None
        if "siliconflow.cn" in openai_base_url():
            extra_body = {"enable_thinking": enable_thinking}
            if enable_thinking:
                extra_body["thinking_budget"] = 512
        client = OpenAI(
            api_key=os.getenv("AGENT_OPENAI_API_KEY"),
            base_url=openai_base_url(),
            timeout=60,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=openai_model_name(),
            messages=messages,
            temperature=temperature,
            max_tokens=512,
            extra_body=extra_body,
            timeout=45,
            max_retries=0,
        )
        message = response.choices[0].message
        return ModelInvocationResult(
            content=FinalAnswerModelClient._content_to_text(getattr(message, "content", "")),
            reasoning_content=FinalAnswerModelClient._response_reasoning_content(message),
        )

    @staticmethod
    def _response_reasoning_content(response: Any) -> str | None:
        additional_kwargs = getattr(response, "additional_kwargs", {}) or {}
        response_metadata = getattr(response, "response_metadata", {}) or {}
        model_extra = getattr(response, "model_extra", {}) or {}
        candidates = [
            getattr(response, "reasoning_content", None),
            getattr(response, "reasoning", None),
            additional_kwargs.get("reasoning_content"),
            additional_kwargs.get("reasoning"),
            additional_kwargs.get("reasoningContent"),
            response_metadata.get("reasoning_content"),
            response_metadata.get("reasoning"),
            model_extra.get("reasoning_content"),
        ]
        for candidate in candidates:
            text = FinalAnswerModelClient._content_to_text(candidate).strip() if candidate is not None else ""
            if text:
                return text
        return None

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
            return "\n".join(parts)
        return str(content)
