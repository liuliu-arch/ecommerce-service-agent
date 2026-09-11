"""第 41 课：真实模型路由客户端。"""

from __future__ import annotations

from course_runtime.course_logging import log_model_input, log_model_output

import json
import os
from typing import Any

from pydantic import BaseModel, Field

from api.schemas import Intent, RoutePlanCandidate, ToolCandidate
from config.settings import api_key_is_missing, load_course_env, openai_base_url, openai_model_name
from prompts.loader import PromptManager, prompt_manager


class ModelRouteResult(BaseModel):
    """模型路由结果。结构化候选只有通过服务端校验后才可能进入最终 RoutePlan。"""

    intent: Intent
    query_plan: dict[str, Any] | None = None
    query_plan_error: str | None = None
    candidate: RoutePlanCandidate | None = None
    used_model: bool = False
    model_name: str | None = None
    fallback_reason: str | None = None
    framework: str | None = None
    prompt_fragments: list[dict[str, Any]] = Field(default_factory=list)


class RouteModelClient:
    """用真实大模型判断本轮应该进入哪条受控路径。"""

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

    def plan_route_candidate(
        self,
        user_message: str,
        *,
        fallback_intent: Intent,
        tool_candidates: list[ToolCandidate],
        query_context: dict[str, Any] | None = None,
    ) -> ModelRouteResult:
        """让模型生成结构化 RoutePlan 候选；失败时保留确定性回退意图。"""
        if not self.can_call_model():
            return ModelRouteResult(intent=fallback_intent, fallback_reason="model_config_missing")
        try:
            model = self._create_chat_model(temperature=0)
            fragments = self.prompt_manager.select_fragments({"phase": "route"})
            system_prompt = self.prompt_manager.render_system_prompt(fragments)
            from tools.query_plan import QueryPlan, PLAN_PROMPT
            if query_context is not None:
                system_prompt += PLAN_PROMPT + json.dumps(QueryPlan.model_json_schema(),ensure_ascii=False)
            model_input = json.dumps(
                {
                    "user_message": user_message,
                    "query_context": query_context,
                    "tool_candidates": [candidate.model_dump() for candidate in tool_candidates],
                },
                ensure_ascii=False,
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": model_input},
            ]
            log_model_input(model=openai_model_name(), messages=messages, prompt_source=__file__)
            content = self._invoke_chain(model, model_input, system_prompt)
            log_model_output(model=openai_model_name(), content=content)
            prompt_fragments = self.prompt_manager.selection_summary(fragments, phase="route")
            payload = self._extract_json_object(content) or {}
            plan = None
            plan_error = None
            if query_context is not None:
                try: plan = QueryPlan.model_validate(payload.get("query_plan")).model_dump(mode="json")
                except ValueError: plan_error = "invalid_or_missing_query_plan"
            candidate = self._extract_candidate(content)
            if candidate is None:
                return ModelRouteResult(
                    intent=fallback_intent,
                    used_model=True,
                    model_name=openai_model_name(),
                    fallback_reason="invalid_model_route_candidate",
                    framework="langchain_runnable_sequence",
                    prompt_fragments=prompt_fragments,
                )
            return ModelRouteResult(
                query_plan=plan,
                query_plan_error=plan_error,
                intent=candidate.intent,
                candidate=candidate,
                used_model=True,
                model_name=openai_model_name(),
                framework="langchain_runnable_sequence",
                prompt_fragments=prompt_fragments,
            )
        except Exception as exc:
            return ModelRouteResult(
                intent=fallback_intent,
                model_name=openai_model_name(),
                fallback_reason=exc.__class__.__name__,
            )

    def plan_intent(self, user_message: str, *, fallback_intent: Intent) -> ModelRouteResult:
        """兼容旧调用；新编排应调用 plan_route_candidate 并传入服务端工具目录。"""
        return self.plan_route_candidate(
            user_message,
            fallback_intent=fallback_intent,
            tool_candidates=[],
        )

    @staticmethod
    def _extract_json_object(content: str) -> dict[str, Any] | None:
        text = content.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            start = text.find("{")
            if start < 0:
                return None
            try:
                payload, _ = decoder.raw_decode(text[start:])
            except (json.JSONDecodeError, TypeError):
                return None
        return payload if isinstance(payload, dict) else None

    @classmethod
    def _extract_candidate(cls, content: str) -> RoutePlanCandidate | None:
        payload = cls._extract_json_object(content)
        if payload is None:
            return None
        try:
            return RoutePlanCandidate.model_validate({k:v for k,v in payload.items() if k != "query_plan"})
        except ValueError:
            return None

    @classmethod
    def _extract_intent(cls, content: str) -> Intent | None:
        """保留给旧课程测试和调试脚本使用；正式链路使用完整候选校验。"""
        payload = cls._extract_json_object(content)
        if payload is None:
            return None
        intent = payload.get("intent")
        allowed = set(Intent.__args__)
        return intent if intent in allowed else None

    @staticmethod
    def _chat_model_class() -> Any:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI

    def _create_chat_model(self, *, temperature: float) -> Any:
        load_course_env()
        chat_model_class = self._chat_model_class()
        return chat_model_class(
            model=openai_model_name(),
            api_key=os.getenv("AGENT_OPENAI_API_KEY"),
            base_url=openai_base_url(),
            temperature=temperature,
            timeout=30,
            max_retries=0,
            extra_body={"enable_thinking": False} if "siliconflow.cn" in openai_base_url() else None,
        )

    @staticmethod
    def _invoke_chain(model: Any, user_message: str, system_prompt: str) -> str:
        """用 LangChain RunnableSequence 执行可替换 Prompt、模型和输出解析。"""
        from langchain_core.messages import SystemMessage
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_prompt),
                ("human", "{user_message}"),
            ]
        )
        chain = prompt | model | StrOutputParser()
        return str(chain.invoke({"user_message": user_message}))
