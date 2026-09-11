"""第 41 课综合演练 Agent 编排层。它复用 Tool、RAG、Workflow、Trace、Eval 和成本治理能力。"""

from __future__ import annotations

from course_runtime.course_logging import observe_chat, observe_operation

from typing import Any

from api.schemas import *
from config.settings import load_course_env
from context.builder import (
    SESSION_MEMORIES,
    build_context,
    consume_pending_clarification,
    remember_pending_clarification,
    update_memory,
)
from cost.governance import build_cost_summary
from hooks.manager import HookManager
from integrations.ecommerce_client import product_query_keyword
from mcp_catalog.catalog import MCP_CATALOG
from models.answer_client import FinalAnswerModelClient, FinalAnswerModelResult
from models.router_client import ModelRouteResult, RouteModelClient
from observability.trace import public_trace_summary, record_initial_chat_trace, record_trace_events, trace_store
from rag.knowledge import REFUND_POLICY, RETURN_POLICY, faq_knowledge_result, low_confidence_result, promotion_policy_result
from safety.source_guard import inspect_source
from state.session_state import MESSAGE_COUNT_BY_SESSION
from tools.langchain_runtime import LangChainToolRunner
from tools.planning import (
    build_order_clarification,
    build_route_plan,
    classify_guard_intent,
    classify_intent,
    classify_route_veto_intent,
    estimate_tokens,
    extract_order_id,
    extract_return_reason,
    route_tool_candidates,
)
from tools.runtime_context import (
    general_chat_answer,
    is_runtime_identity_query,
    logistics_status_label,
    order_no,
    order_status_label,
    runtime_context_summary,
    runtime_identity_answer,
)
from tools.tool_runtime import get_order_detail, get_order_logistics, get_refund_status, search_products
from workflows.after_sale_graph import RECEIVED_RETURN_GRAPH, REFUND_APPROVAL_GRAPH
from workflows.resume import resume_from_checkpoint

from tools.read_queries import (boundary_kind, knowledge_question, is_collection_query,
    list_orders, detail_answer, product_answer, BOUNDARY_ANSWERS)

from tools.query_plan import QueryPlan, model_context, remember_plan

class Lesson41Agent:
    """第十幕综合演练版：复用前面能力，服务大促总演习和项目答辩验证。"""

    def __init__(self) -> None:
        self.route_model_client = RouteModelClient()
        self.answer_model_client = FinalAnswerModelClient()
        self.langchain_tool_runner = LangChainToolRunner()

    @observe_chat
    def chat(self, request: ChatRequest) -> ChatResponse:
        """编排总演习聊天链路，串联 Tool、RAG、Workflow/HITL、降级、安全、Trace 和成本治理。"""
        load_course_env()
        MESSAGE_COUNT_BY_SESSION[request.session_id] = MESSAGE_COUNT_BY_SESSION.get(request.session_id, 0) + 1
        message_count = MESSAGE_COUNT_BY_SESSION[request.session_id]
        explicit_order_id = extract_order_id(request.user_message)
        classified_intent = classify_intent(request.user_message)
        resolved_clarification, clarification_transition = consume_pending_clarification(
            session_id=request.session_id,
            runtime_user_id=request.runtime_user_id,
            current_intent=classified_intent,
            supplied_fields={"order_id": explicit_order_id},
            current_message_count=message_count,
        )
        fallback_intent = (
            resolved_clarification["intent"]
            if resolved_clarification is not None
            else classified_intent
        )
        if resolved_clarification is not None:
            # 参数续接由受控 Session 状态完成，不再让模型仅凭一个订单号重猜意图。
            route_result = ModelRouteResult(
                intent=fallback_intent,
                fallback_reason="pending_clarification_resolved",
                framework="structured_session_state",
            )
        else:
            route_result = self.route_model_client.plan_route_candidate(
                request.user_message,
                fallback_intent=fallback_intent,
                tool_candidates=route_tool_candidates(),
                query_context=model_context(request),
            )
        route_result = self._apply_route_guard(
            user_message=request.user_message,
            route_result=route_result,
        )
        intent = route_result.intent
        query_plan = QueryPlan.model_validate(route_result.query_plan) if route_result.query_plan else None
        # Raw user text still governs security/workflow; model plans can only refine reads.
        if query_plan and intent not in {"order_query","product_query","faq_query","promotion_query","low_confidence_query"}:
            query_plan = None
        if query_plan and ((intent == "order_query" and query_plan.target != "orders") or (intent == "product_query" and query_plan.target != "products")):
            query_plan = None
        read_kind = boundary_kind(request.user_message) if intent != "security_request" else None
        if read_kind:
            intent = "faq_query" if read_kind == "policy" else "general_chat"
        elif intent in {"order_query", "product_query"}:
            read_kind = "orders" if intent == "order_query" else "products"
        order_id, context_report, compression_report = build_context(request, explicit_order_id)
        if query_plan and query_plan.target == "orders" and query_plan.order_ids:
            order_id = query_plan.order_ids[0]
        route_was_guarded = str(route_result.fallback_reason or "").startswith(
            ("rule_guard_", "rule_veto_")
        )
        route_plan = build_route_plan(
            intent=intent,
            user_message=request.user_message,
            order_id=order_id,
            model_candidate=route_result.candidate if not route_was_guarded else None,
        )
        runtime_context = runtime_context_summary(request)
        uses_runtime_identity = is_runtime_identity_query(request.user_message)
        citations: list[Citation] = []
        tool_calls: list[ToolCallTrace] = []
        workflow: dict[str, Any] | None = None
        cache_hit = False
        common_cache_key: str | None = None
        degraded = False
        degradation_reason: str | None = None
        rag_rerank: dict[str, Any] | None = None
        rag_retrieval: dict[str, Any] | None = None
        verified_order_id: str | None = None
        verified_product_name: str | None = None
        collection_query = read_kind == "orders" and (query_plan.scope in {"collection","latest"} if query_plan else is_collection_query(request.user_message) and not explicit_order_id)
        if collection_query:
            route_plan = route_plan.model_copy(update={"required_tools":["list_user_orders"],"fallback_policy":"tool_first","entity_refs":[]})
        clarification = None if collection_query or read_kind in BOUNDARY_ANSWERS or read_kind in {"identity", "policy", "products"} else build_order_clarification(request, route_plan)
        if query_plan and (query_plan.clarification or query_plan.order_ids or query_plan.unsupported_action != "none"):
            clarification = None
        if clarification:
            remember_pending_clarification(
                session_id=request.session_id,
                runtime_user_id=request.runtime_user_id,
                intent=intent,
                required_field=clarification.clarification_field,
                current_message_count=message_count,
            )
        hooks = HookManager()
        tool_calling_state: dict[str, Any] = {
            "create_agent": False,
            "skip_reason": "route_does_not_need_business_tools",
            "available_tools": route_plan.required_tools,
            "selected_tools": [],
            "message_types": [],
            "tool_message_count": 0,
            "fallback_used": False,
        }
        tool_agent_prompt_fragments: list[dict[str, Any]] = []
        tool_agent_model_calls = 0

        record_initial_chat_trace(
            session_id=request.session_id,
            runtime_user_id=request.runtime_user_id,
            runtime_nickname=request.runtime_nickname,
            runtime_member_level=request.runtime_member_level,
            runtime_risk_level=request.runtime_risk_level,
            intent=intent,
            estimated_tokens=estimate_tokens(request.user_message),
            route_result=route_result,
            context_report=context_report,
            compression_report=compression_report,
        )
        if resolved_clarification is not None:
            trace_store.add(
                request.session_id,
                "tool_clarification_resolved",
                {
                    "session_id": request.session_id,
                    "resolved_fields": resolved_clarification["required_fields"],
                    "restored_intent": resolved_clarification["intent"],
                    "status": "resolved",
                },
            )
        elif clarification_transition == "turn_window_elapsed":
            trace_store.add(
                request.session_id,
                "tool_clarification_expired",
                {
                    "session_id": request.session_id,
                    "reason": clarification_transition,
                    "status": "expired",
                },
            )
        trace_store.add(
            request.session_id,
            "route_plan_built",
            {
                "session_id": request.session_id,
                "intent": route_plan.intent,
                "source": route_plan.source,
                "required_tools": route_plan.required_tools,
                "knowledge_domains": route_plan.knowledge_domains,
                "needs_rag": route_plan.needs_rag,
                "needs_business_tools": route_plan.needs_business_tools,
                "requires_workflow": route_plan.requires_workflow,
                "risk_level": route_plan.risk_level,
                "fallback_policy": route_plan.fallback_policy,
                "policy_constraints": route_plan.policy_constraints,
            },
        )
        if clarification:
            trace_store.add(
                request.session_id,
                "tool_clarification_required",
                {
                    "session_id": request.session_id,
                    "clarification_field": clarification.clarification_field,
                    "candidate_count": len(clarification.candidates),
                    "candidate_order_ids": [candidate.value for candidate in clarification.candidates],
                    "pending_intent": intent,
                    "status": "waiting_for_user",
                },
            )

        trace_store.add(request.session_id, "semantic_query_planned", {"session_id":request.session_id,"plan":query_plan.model_dump(mode="json") if query_plan else None,"error":route_result.query_plan_error,"used_model":route_result.used_model})
        if read_kind and not uses_runtime_identity:
            def begin_read(name, arguments):
                hooks.pre_tool_call(name, arguments, request.runtime_user_id)
                trace_store.add(request.session_id, "tool_started", {"session_id":request.session_id,"tool_name":name})
            risk_level = "low"
            next_action = "answer_user"
            needs_human_approval = False
            if query_plan and query_plan.clarification:
                answer = query_plan.clarification
                next_action = "ask_clarification"
            elif query_plan and query_plan.unsupported_action != "none":
                answer = "我目前不能代你修改收件联系方式、地址、取消订单或发放优惠券，本次没有执行这些操作。请在订单详情查看可用操作，或联系商家人工客服核实。"
                next_action = "transfer_to_human"
            elif route_result.query_plan_error and read_kind in {"orders","products"}:
                answer = "这次没有可靠解析出查询条件，请补充要查询的商品、订单或筛选范围。"
                next_action = "ask_clarification"
            elif read_kind in BOUNDARY_ANSWERS:
                answer = BOUNDARY_ANSWERS[read_kind]
                next_action = "transfer_to_human"
            elif read_kind == "orders":
                if collection_query:
                    begin_read("list_user_orders", {})
                    answer, call = list_orders(request, query_plan)
                    tool_calls = [call]
                elif clarification:
                    answer = clarification.message
                    choices = '；'.join(f'{c.value}（{c.hint}）' for c in clarification.candidates)
                    if choices: answer += ' 当前账号订单：' + choices
                    next_action = "ask_clarification"
                else:
                    ids = query_plan.order_ids if query_plan and query_plan.order_ids else [order_id]
                    answers = []
                    for selected_id in ids:
                        one_answer, calls, verified = detail_answer(request, selected_id, before=begin_read, plan=query_plan)
                        answers.append(one_answer)
                        tool_calls.extend(calls)
                        if len(ids) == 1: verified_order_id = verified
                    answer = "\n".join(answers)
            elif read_kind == "products":
                begin_read("search_products", {"query":request.user_message})
                answer, call, verified_product_name = product_answer(request, query_plan)
                tool_calls = [call]
            else:
                answer = ""
            for call in tool_calls:
                hooks.post_tool_call(call)
                trace_store.add(request.session_id, "tool_finished", {"session_id":request.session_id,"tool_name":call.tool_name,"status":call.status,"error_type":call.error_type,"fact_source":call.arguments.get("fact_source")})
                if call.next_action: next_action = call.next_action
                if call.error_type == "business_api_unavailable":
                    degraded = True
                    degradation_reason = call.error_type
            if query_plan and tool_calls and all(c.status == "success" for c in tool_calls) and next_action == "answer_user":
                remember_plan(request,query_plan,verified_product_name if read_kind == "products" else None)
            tool_calling_state = {"create_agent":False,"skip_reason":"typed_readonly_dispatch","selected_tools":[c.tool_name for c in tool_calls],"model_calls":0}
            policy_question = request.user_message if read_kind == "policy" else knowledge_question(request.user_message) if read_kind in {"orders", "products"} else ""
            if query_plan and query_plan.policy_question: policy_question = query_plan.policy_question
            if policy_question and not degraded:
                from rag.grounded_pipeline import grounded_knowledge_result
                from rag.domains import PUBLIC_DOMAINS, infer_public_domains
                domains = ["received_return_policy", "after_sale_policy"] if read_kind == "policy" else sorted(infer_public_domains(policy_question) or PUBLIC_DOMAINS)
                knowledge_result = grounded_knowledge_result(request.session_id, policy_question, "faq_query", domains)
                record_trace_events(request.session_id, knowledge_result.trace_events)
                citations = knowledge_result.citations
                rag_retrieval = knowledge_result.retrieval_debug
                rag_rerank = knowledge_result.rerank
                answer = (answer + "\n" + knowledge_result.answer).strip()
                if knowledge_result.next_action == "transfer_to_human": next_action = "transfer_to_human"
        elif uses_runtime_identity:
            answer = runtime_identity_answer(request)
            risk_level = "low"
            next_action = "answer_user"
            needs_human_approval = False
            trace_store.add(
                request.session_id,
                "runtime_identity_answered",
                {
                    "session_id": request.session_id,
                    "intent": intent,
                    "runtime_user_id": request.runtime_user_id,
                    "used_runtime_context": True,
                },
            )
        elif intent == "degradation_request":
            degraded = True
            degradation_reason = "business_tool_unavailable"
            degradation_source = (
                "explicit_course_fault_injection"
                if "故障注入演示" in request.user_message
                else "user_reported_service_failure"
            )
            trace_store.add(
                request.session_id,
                "degradation_triggered",
                {
                    "session_id": request.session_id,
                    "intent": intent,
                    "degraded": True,
                    "reason": degradation_reason,
                    "source": degradation_source,
                },
            )
            answer = "订单或物流服务暂时不可用，本轮不继续猜测业务事实。建议稍后重试，或转人工客服继续核验。"
            risk_level = "medium"
            next_action = "transfer_to_human"
            needs_human_approval = False
        elif intent == "security_request":
            trace_store.add(
                request.session_id,
                "prompt_security_blocked",
                {"session_id": request.session_id, "intent": intent, "risk_level": "high", "status": "blocked"},
            )
            answer = "我不能提供受保护系统信息、受保护推理摘要、工具细节或内部策略。"
            risk_level: RiskLevel = "high"
            next_action: NextAction = "answer_user"
            needs_human_approval = False
        elif intent == "low_confidence_query":
            knowledge_result = faq_knowledge_result(request.session_id, query_plan.normalized_question if query_plan else request.user_message, knowledge_domains=route_plan.knowledge_domains)
            rag_retrieval = knowledge_result.retrieval_debug
            rag_rerank = knowledge_result.rerank
            record_trace_events(request.session_id, knowledge_result.trace_events)
            answer = knowledge_result.answer
            citations = knowledge_result.citations
            risk_level = knowledge_result.risk_level
            next_action = knowledge_result.next_action
            needs_human_approval = knowledge_result.needs_human_approval
        elif intent == "faq_query":
            knowledge_result = faq_knowledge_result(request.session_id, query_plan.normalized_question if query_plan else request.user_message, knowledge_domains=route_plan.knowledge_domains)
            if not knowledge_result.citations:
                intent = "low_confidence_query"
            record_trace_events(request.session_id, knowledge_result.trace_events)
            answer = knowledge_result.answer
            if knowledge_result.cache_hit and request.runtime_nickname:
                # 缓存只保存公共知识，命中后再用本轮可信 Runtime Context 渲染称呼。
                answer = f"{request.runtime_nickname}，{answer}"
            citations = knowledge_result.citations
            risk_level = knowledge_result.risk_level
            next_action = knowledge_result.next_action
            needs_human_approval = knowledge_result.needs_human_approval
            cache_hit = knowledge_result.cache_hit
            common_cache_key = knowledge_result.cache_key
            rag_retrieval = knowledge_result.retrieval_debug
            rag_rerank = knowledge_result.rerank
        elif intent == "promotion_query":
            knowledge_result = promotion_policy_result(request.session_id, query_plan.normalized_question if query_plan else request.user_message, knowledge_domains=route_plan.knowledge_domains)
            if not knowledge_result.citations:
                intent = "low_confidence_query"
            record_trace_events(request.session_id, knowledge_result.trace_events)
            answer = knowledge_result.answer
            citations = knowledge_result.citations
            rag_rerank = knowledge_result.rerank
            rag_retrieval = knowledge_result.retrieval_debug
            risk_level = knowledge_result.risk_level
            next_action = knowledge_result.next_action
            needs_human_approval = knowledge_result.needs_human_approval
        elif intent == "return_request":
            if clarification:
                answer = clarification.message
                risk_level = "high"
                next_action = "ask_clarification"
                needs_human_approval = False
            else:
                hooks.pre_tool_call("get_order_detail", {"order_id": order_id}, request.runtime_user_id)
                trace_store.add(
                    request.session_id,
                    "tool_started",
                    {"session_id": request.session_id, "tool_name": "get_order_detail", "order_id": order_id},
                )
                order, detail_call = get_order_detail(order_id, request.runtime_user_id, request.runtime_context)
                hooks.post_tool_call(detail_call)
                tool_calls.append(detail_call)
                trace_store.add(
                    request.session_id,
                    "tool_finished",
                    {
                        "session_id": request.session_id,
                        "tool_name": detail_call.tool_name,
                        "order_id": order_id,
                        "status": detail_call.status,
                        "risk_level": detail_call.risk_level,
                    },
                )
                if order is None:
                    answer = detail_call.output_summary
                    risk_level = "high"
                    next_action = "transfer_to_human"
                    needs_human_approval = False
                else:
                    verified_order_id = order_no(order)
                    return_reason = extract_return_reason(request.user_message)
                    citations.append(RETURN_POLICY)
                    trace_store.add(
                        request.session_id,
                        "rag_pre_retrieved",
                        {
                            "session_id": request.session_id,
                            "hit_count": 1,
                            "retrieval_stage": "pre_retrieval",
                            "policy_id": "return_after_delivery",
                        },
                    )
                    workflow = RECEIVED_RETURN_GRAPH.run(order, return_reason=return_reason, citations=citations)
                    eligible = workflow["eligibility_status"] == "eligible_for_application"
                    reason_labels = {
                        "order_not_received": "订单尚未签收",
                        "product_not_returnable": "商品不支持无理由退货",
                        "product_returnability_unknown": "暂未核实商品可退属性",
                        "signed_time_missing": "缺少可信签收时间",
                        "signed_time_in_future": "签收时间晚于当前业务日期，需要核实",
                        "return_window_expired": "签收已超过 7 天",
                        "return_reason_missing": "还需要补充明确的退货原因",
                    }
                    answer = (
                        f"订单 {order_no(order)} 已根据电商公司签收后退货 SOP，完成签收时间、商品可退属性、退货原因和七天窗口检查，可以准备退货申请；当前还不是退货成功，仍需人工复核。"
                        if eligible
                        else f"订单 {order_no(order)} 暂不满足签收后退货条件：{reason_labels.get(workflow['eligibility_reason'], workflow['eligibility_reason'])}。"
                    )
                    risk_level = "high"
                    next_action = "transfer_to_human" if eligible else "answer_user"
                    needs_human_approval = eligible
                    trace_store.add(request.session_id, "received_return_workflow_completed", {"session_id": request.session_id, **workflow})
        elif intent in {"order_query", "refund_status_query", "refund_request", "product_query"}:
            tool_result = self.langchain_tool_runner.run(
                request=request,
                intent=intent,
                required_tools=route_plan.required_tools,
                hooks=hooks,
                expected_order_id=order_id,
                expected_product_keyword=product_query_keyword(request.user_message) if intent == "product_query" else None,
            )
            tool_calling_state = tool_result.state
            tool_agent_prompt_fragments = tool_result.prompt_fragments
            tool_agent_model_calls = tool_result.model_calls
            trace_store.add(
                request.session_id,
                "langchain_tool_agent_completed",
                {
                    "session_id": request.session_id,
                    "create_agent": tool_calling_state.get("create_agent"),
                    "selected_tools": tool_calling_state.get("selected_tools", []),
                    "message_types": tool_calling_state.get("message_types", []),
                    "fallback_used": tool_calling_state.get("fallback_used"),
                    "status": "success" if tool_result.executed else "fallback",
                },
            )
            if tool_result.executed:
                order = tool_result.order
                tool_calls.extend(tool_result.tool_calls)
                detail_call = tool_calls[0]
                for call in tool_result.tool_calls:
                    trace_store.add(
                        request.session_id,
                        "tool_started",
                        {"session_id": request.session_id, "tool_name": call.tool_name, "order_id": order_id},
                    )
                    trace_store.add(
                        request.session_id,
                        "tool_finished",
                        {
                            "session_id": request.session_id,
                            "tool_name": call.tool_name,
                            "order_id": order_id,
                            "status": call.status,
                            "risk_level": call.risk_level,
                            "next_action": call.next_action,
                        },
                    )
            elif clarification is None and intent == "product_query":
                hooks.pre_tool_call("search_products", {"keyword": request.user_message}, request.runtime_user_id)
                trace_store.add(
                    request.session_id,
                    "tool_started",
                    {"session_id": request.session_id, "tool_name": "search_products"},
                )
                products, product_call = search_products(request.user_message)
                tool_calls.append(product_call)
                hooks.post_tool_call(product_call)
                trace_store.add(
                    request.session_id,
                    "tool_finished",
                    {
                        "session_id": request.session_id,
                        "tool_name": product_call.tool_name,
                        "status": product_call.status,
                        "risk_level": product_call.risk_level,
                    },
                )
                order = None
                detail_call = None
            elif clarification is None:
                hooks.pre_tool_call("get_order_detail", {"order_id": order_id}, request.runtime_user_id)
                trace_store.add(
                    request.session_id,
                    "tool_started",
                    {"session_id": request.session_id, "tool_name": "get_order_detail", "order_id": order_id},
                )
                order, detail_call = get_order_detail(order_id, request.runtime_user_id, request.runtime_context)
                tool_calls.append(detail_call)
                hooks.post_tool_call(detail_call)
                trace_store.add(
                    request.session_id,
                    "tool_finished",
                    {
                        "session_id": request.session_id,
                        "tool_name": detail_call.tool_name,
                        "order_id": order_id,
                        "status": detail_call.status,
                        "risk_level": detail_call.risk_level,
                        "next_action": detail_call.next_action,
                    },
                )
            else:
                order = None
                detail_call = None
            if order is not None:
                verified_order_id = order_no(order)
            if clarification:
                answer = clarification.message
                if clarification.candidates:
                    choices = "；".join(f"{candidate.value}（{candidate.hint}）" for candidate in clarification.candidates)
                    answer = f"{answer} 当前账号下可选订单：{choices}。"
                risk_level = "medium"
                next_action = "ask_clarification"
                needs_human_approval = False
            elif intent == "order_query" and order:
                logistics_call = next((call for call in tool_calls if call.tool_name == "get_order_logistics"), None)
                if logistics_call is None:
                    hooks.pre_tool_call("get_order_logistics", {"order_id": order_id}, request.runtime_user_id)
                    logistics_call = get_order_logistics(order)
                    tool_calls.append(logistics_call)
                    hooks.post_tool_call(logistics_call)
                    trace_store.add(
                        request.session_id,
                        "tool_finished",
                        {
                            "session_id": request.session_id,
                            "tool_name": logistics_call.tool_name,
                            "order_id": order_id,
                            "status": logistics_call.status,
                            "risk_level": logistics_call.risk_level,
                        },
                    )
                answer = f"我帮你查到了，订单 {order_no(order)} 目前{order_status_label(order)}，物流状态是{logistics_status_label(order)}。"
                risk_level = "low"
                next_action = "answer_user"
                needs_human_approval = False
            elif intent == "refund_status_query" and order:
                status_call = next((call for call in tool_calls if call.tool_name == "get_refund_status"), None)
                if status_call is None:
                    hooks.pre_tool_call("get_refund_status", {"order_id": order_id}, request.runtime_user_id)
                    trace_store.add(
                        request.session_id,
                        "tool_started",
                        {"session_id": request.session_id, "tool_name": "get_refund_status", "order_id": order_id},
                    )
                    status_call = get_refund_status(order, request.runtime_user_id)
                    tool_calls.append(status_call)
                    hooks.post_tool_call(status_call)
                    trace_store.add(
                        request.session_id,
                        "tool_finished",
                        {
                            "session_id": request.session_id,
                            "tool_name": status_call.tool_name,
                            "order_id": order_id,
                            "status": status_call.status,
                            "risk_level": status_call.risk_level,
                        },
                    )
                answer = status_call.output_summary
                risk_level = status_call.risk_level
                next_action = status_call.next_action or "answer_user"
                needs_human_approval = False
                if status_call.status == "error":
                    degraded = True
                    degradation_reason = status_call.error_type or "refund_status_unavailable"
            elif intent == "product_query":
                product_call = next((call for call in tool_calls if call.tool_name == "search_products"), None)
                if product_call is None:
                    products, product_call = search_products(request.user_message)
                    tool_calls.append(product_call)
                if any(term in request.user_message for term in ["活动", "优惠", "满减", "会员"]):
                    knowledge_result = promotion_policy_result(request.session_id, query_plan.normalized_question if query_plan else request.user_message, knowledge_domains=route_plan.knowledge_domains)
                    record_trace_events(request.session_id, knowledge_result.trace_events)
                    citations = knowledge_result.citations
                    rag_retrieval = knowledge_result.retrieval_debug
                    rag_rerank = knowledge_result.rerank
                    policy_answer = (
                        f"平台通用规则：{knowledge_result.answer} "
                        "这不代表该规则一定适用于当前商品活动，具体组合以商品页和结算页为准。"
                        if citations
                        else "活动规则请以商品页与结算页为准。"
                    )
                    answer = f"{product_call.output_summary} {policy_answer}"
                else:
                    answer = product_call.output_summary
                risk_level = "low" if product_call.status == "success" else "medium"
                next_action = product_call.next_action or "answer_user"
                needs_human_approval = False
                if product_call.status == "success":
                    verified_product_name = str(product_call.arguments.get("product_name") or "") or None
            elif intent == "refund_request":
                citations.append(REFUND_POLICY)
                trace_store.add(
                    request.session_id,
                    "rag_pre_retrieved",
                    {
                        "session_id": request.session_id,
                        "hit_count": 1,
                        "retrieval_stage": "pre_retrieval",
                        "policy_id": "refund_before_shipping",
                    },
                )
                eligible, eligibility_reason = REFUND_APPROVAL_GRAPH.assess_eligibility(order)
                if not eligible:
                    workflow = None
                    answer = (
                        "该订单已经发货，不能进入未发货退款审批；请按签收后的退货或售后流程处理。"
                        if eligibility_reason == "order_already_shipped_or_not_eligible"
                        else "订单事实或支付状态没有通过退款资格校验，暂不能创建退款审批，请转人工核验。"
                    )
                    risk_level = "high"
                    next_action = "transfer_to_human"
                    needs_human_approval = False
                    trace_store.add(
                        request.session_id,
                        "refund_eligibility_blocked",
                        {"session_id": request.session_id, "order_id": order_id, "reason": eligibility_reason, "status": "blocked"},
                    )
                else:
                    workflow = REFUND_APPROVAL_GRAPH.run(
                        request=request,
                        order=order,
                        order_id=order_id,
                        citations=citations,
                    )
                if workflow is None:
                    pass
                else:
                    for node_name in workflow.get("node_history", []):
                        trace_store.add(
                            request.session_id,
                            "workflow_node_finished",
                            {
                                "session_id": request.session_id,
                                "workflow_id": workflow["workflow_id"],
                                "graph_name": workflow.get("graph_name"),
                                "node_name": node_name,
                                "status": "completed",
                            },
                        )
                    trace_store.add(
                        request.session_id,
                        "workflow_completed",
                        {
                            "session_id": request.session_id,
                            **workflow,
                            "risk_level": "high",
                            "needs_human_approval": True,
                        },
                    )
                    trace_store.add(
                        request.session_id,
                        "human_approval_required",
                        {
                            "session_id": request.session_id,
                            "workflow_id": workflow["workflow_id"],
                            "pending_action": "require_approval",
                            "risk_level": "high",
                            "needs_human_approval": True,
                        },
                    )
                    answer = f"{order_no(order)} 可以进入未发货退款申请判断，但资金动作必须等待人工审批。"
                    risk_level = "high"
                    next_action = "transfer_to_human"
                    needs_human_approval = True
            else:
                answer = detail_call.output_summary
                risk_level = "medium"
                next_action = "ask_clarification" if detail_call.error_type == "missing_order_id" else "transfer_to_human"
                needs_human_approval = False
        else:
            answer = general_chat_answer(request.user_message)
            risk_level = "low"
            next_action = "answer_user"
            needs_human_approval = False

        if any(call.error_type == "business_api_unavailable" for call in tool_calls):
            degraded = True
            degradation_reason = "business_api_unavailable"
            next_action = "transfer_to_human"
        # Tool/RAG 文本也是外部数据，进入最终模型前必须按来源做污染检查。
        external_reports: list[dict[str, Any]] = []
        for call in tool_calls:
            report = inspect_source("tool_result", call.output_summary)
            if report["tainted"]:
                call.output_summary = str(report["sanitized_content"])
            external_reports.append({key: value for key, value in report.items() if key != "sanitized_content"})
        for citation in citations:
            report = inspect_source("rag_document", citation.snippet)
            if report["tainted"]:
                citation.snippet = str(report["sanitized_content"])
            external_reports.append({key: value for key, value in report.items() if key != "sanitized_content"})
        if external_reports:
            source_safety = context_report["source_safety"]
            source_safety["reports"].extend(external_reports)
            source_safety["tainted"] = source_safety["tainted"] or any(report["tainted"] for report in external_reports)
            source_safety["tainted_sources"] = sorted(
                set(source_safety["tainted_sources"])
                | {report["source"] for report in external_reports if report["tainted"]}
            )
            trace_store.add(
                request.session_id,
                "context_source_safety_checked",
                {
                    "session_id": request.session_id,
                    "tainted": source_safety["tainted"],
                    "tainted_sources": source_safety["tainted_sources"],
                    "source_count": len(source_safety["reports"]),
                },
            )

        if rag_retrieval:
            trace_store.add(
                request.session_id,
                "rag_hybrid_retrieved",
                {
                    "session_id": request.session_id,
                    "mode": rag_retrieval.get("mode"),
                    "rewritten_query": (rag_retrieval.get("plan") or {}).get("rewritten_query"),
                    "index_version": rag_retrieval.get("index_version"),
                    "index_chunk_count": rag_retrieval.get("index_chunk_count"),
                    "index_cache_hit": rag_retrieval.get("index_cache_hit"),
                    "retrieval_cache_hit": rag_retrieval.get("retrieval_cache_hit"),
                    "vector_policy_ids": rag_retrieval.get("vector_policy_ids", []),
                    "keyword_policy_ids": rag_retrieval.get("keyword_policy_ids", []),
                    "faq_selection": rag_retrieval.get("faq_selection"),
                    "hit_count": len(citations),
                    "retrieval_stage": "hybrid_retrieval",
                },
            )

        model_answer = self._compose_final_answer(
            request=request,
            intent=intent,
            answer=answer,
            risk_level=risk_level,
            next_action=next_action,
            tool_calls=tool_calls,
            citations=citations,
            workflow=workflow,
            cache_hit=cache_hit,
            degraded=degraded,
            skip_final_model=uses_runtime_identity or bool(read_kind),
            enable_reasoning=request.reasoning_view == "teaching",
            context_report=context_report,
        )
        if model_answer.validation is not None:
            trace_store.add(request.session_id, "answer_grounding_checked", {"session_id": request.session_id, **model_answer.validation})
        answer = model_answer.answer
        reasoning_content = model_answer.reasoning_content if request.reasoning_view == "teaching" else None
        prompt_fragments = [
            *route_result.prompt_fragments,
            *tool_agent_prompt_fragments,
            *model_answer.prompt_fragments,
        ]
        selected_mcp_tool = next((call.tool_name for call in reversed(tool_calls) if call.status == "success"), None)
        mcp_binding = MCP_CATALOG.binding_summary(selected_mcp_tool, risk_level)
        trace_store.add(request.session_id, "mcp_binding_resolved", {"session_id": request.session_id, **mcp_binding})

        if prompt_fragments:
            trace_store.add(
                request.session_id,
                "prompt_context_built",
                {
                    "session_id": request.session_id,
                    "registry_schema": "prompt_registry_v1",
                    "selected_fragments": prompt_fragments,
                    "prompt_body_exposed": False,
                },
            )

        memory = update_memory(
            session_id=request.session_id,
            runtime_user_id=request.runtime_user_id,
            intent=intent,
            verified_order_id=verified_order_id,
            user_message=request.user_message,
            verified_product_name=verified_product_name,
        )
        hook_completion = hooks.on_completion(risk_level=risk_level, next_action=next_action, degraded=degraded)
        for hook_event in hooks.events:
            trace_store.add(request.session_id, "hook_executed", {"session_id": request.session_id, **hook_event})
        cost_summary = build_cost_summary(
            request=request,
            intent=intent,
            tool_calls=tool_calls,
            citations=citations,
            workflow=workflow,
            answer=answer,
            cache_hit=cache_hit,
            common_cache_key=common_cache_key,
            route_model_used=route_result.used_model,
            answer_model_used=model_answer.used_model,
            reasoning_content_returned=bool(reasoning_content),
            reasoning_source=model_answer.reasoning_source,
            degraded=degraded,
            degradation_reason=degradation_reason,
            prompt_fragments=prompt_fragments,
            tool_agent_model_calls=tool_agent_model_calls,
            rag_debug=rag_retrieval,
            answer_validation=model_answer.validation,
        )
        trace_store.add(
            request.session_id,
            "cost_recorded",
            cost_summary,
        )
        trace_store.add(
            request.session_id,
            "final_answer_generated",
            {
                "session_id": request.session_id,
                "intent": intent,
                "status": "success",
                "risk_level": risk_level,
                "used_model": model_answer.used_model,
                "reasoning_content_returned": bool(reasoning_content),
            },
        )

        return ChatResponse(
            session_id=request.session_id,
            answer=answer,
            citations=citations,
            tool_calls=tool_calls,
            clarification=clarification,
            reasoning_summary=[
                "Trace 记录的是公开执行摘要：Runtime Context、Context、Tool、RAG、Workflow/HITL、Hooks 和 Cost。",
                "tool_calls 与 citations 是可观察证据，不是 hidden CoT。",
                "教学模式会尝试展示主链路最终模型返回的 reasoning_content；系统提示词、密钥、隐私原文和内部堆栈不会写入公开 trace。",
            ],
            reasoning_content=reasoning_content,
            session_state={
                "agent_version": "ecommerce-agent",
                "message_count": message_count,
                "intent": intent,
                "model": {
                    "route_planner": {
                        "used_model": route_result.used_model,
                        "model_name": route_result.model_name,
                        "fallback_reason": route_result.fallback_reason,
                        "candidate_validated": route_result.candidate is not None,
                        "candidate_applied": route_plan.source == "llm_with_policy_constraints",
                        "candidate": route_result.candidate.model_dump() if route_result.candidate else None,
                        "prompt_fragments": route_result.prompt_fragments,
                    },
                    "final_answer": {
                        "used_model": model_answer.used_model,
                        "model_name": model_answer.model_name,
                        "fallback_reason": model_answer.fallback_reason,
                        "validation": model_answer.validation,
                        "prompt_fragments": model_answer.prompt_fragments,
                    },
                },
                "prompt_registry": {
                    "schema_version": "prompt_registry_v1",
                    "selected_fragments": prompt_fragments,
                    "selected_fragment_ids": [fragment["name"] for fragment in prompt_fragments],
                    "prompt_body_exposed": False,
                },
                "route_plan": route_plan.model_dump(),
                "tool_calling": {
                    **tool_calling_state,
                    "clarification": clarification.model_dump() if clarification else None,
                },
                "mcp": mcp_binding,
                "frameworks": {
                    "langchain": {
                        "used": route_result.used_model or model_answer.used_model,
                        "route_chain": route_result.framework,
                        "final_answer_chain": model_answer.framework,
                        "prompt_registry": "prompts/prompt_registry.yml",
                        "selected_fragment_ids": [fragment["name"] for fragment in prompt_fragments],
                        "create_agent": bool(tool_calling_state.get("create_agent")),
                    },
                    "langgraph": {
                        "used": bool(workflow and workflow.get("used_langgraph")),
                        "graph_name": workflow.get("graph_name") if workflow else None,
                        "current_node": workflow.get("current_node") if workflow else None,
                        "node_history": workflow.get("node_history", []) if workflow else [],
                    },
                },
                "risk_level": risk_level,
                "next_action": next_action,
                "needs_human_approval": needs_human_approval,
                "runtime_context": runtime_context,
                "memory": memory,
                "context_report": context_report,
                "compression_report": compression_report,
                "hook_events": hooks.events,
                "hook_completion": hook_completion,
                "workflow": workflow,
                "rag": {
                    "low_confidence": intent == "low_confidence_query" or bool((rag_retrieval or {}).get("missing_questions")),
                    "coverage": (rag_retrieval or {}).get("coverage"),
                    "missing_questions": (rag_retrieval or {}).get("missing_questions", []),
                    "secondary_retrieval_count": (rag_retrieval or {}).get("secondary_retrieval_count", 0),
                    "retrievals": (rag_retrieval or {}).get("retrievals", []),
                    "hit_count": len(citations),
                    "citation_ids": [citation.metadata.get("policy_id") for citation in citations if citation.metadata],
                    "rerank_mode": rag_rerank["mode"] if rag_rerank else None,
                    "reranked_policy_ids": rag_rerank["policy_ids"] if rag_rerank else [],
                    "rerank_scores": rag_rerank["scores"] if rag_rerank else {},
                    "rerank_reasons": rag_rerank["reasons"] if rag_rerank else {},
                    "model_rerank": rag_retrieval.get("model_rerank") if rag_retrieval else None,
                    "retrieval_mode": rag_retrieval.get("mode") if rag_retrieval else None,
                    "rewritten_query": (rag_retrieval.get("plan") or {}).get("rewritten_query") if rag_retrieval else None,
                    "index_version": rag_retrieval.get("index_version") if rag_retrieval else None,
                    "index_chunk_count": rag_retrieval.get("index_chunk_count") if rag_retrieval else 0,
                    "index_cache_hit": rag_retrieval.get("index_cache_hit") if rag_retrieval else False,
                    "retrieval_cache_hit": rag_retrieval.get("retrieval_cache_hit") if rag_retrieval else False,
                    "vector_policy_ids": rag_retrieval.get("vector_policy_ids", []) if rag_retrieval else [],
                    "keyword_policy_ids": rag_retrieval.get("keyword_policy_ids", []) if rag_retrieval else [],
                    "source_scores": rag_retrieval.get("source_scores", {}) if rag_retrieval else {},
                    "faq_selection": rag_retrieval.get("faq_selection") if rag_retrieval else None,
                    "embedding": rag_retrieval.get("embedding") if rag_retrieval else None,
                },
                "degraded": degraded,
                "cost_summary": cost_summary,
                "trace": public_trace_summary(request.session_id),
                "next_gap": "第十幕用同一阶段 Agent 做大促总演习，并把证据整理成项目答辩表达。",
            },
        )

    def _compose_final_answer(
        self,
        *,
        request: ChatRequest,
        intent: Intent,
        answer: str,
        risk_level: str,
        next_action: str,
        tool_calls: list[ToolCallTrace],
        citations: list[Citation],
        workflow: dict[str, Any] | None,
        cache_hit: bool,
        degraded: bool,
        skip_final_model: bool = False,
        enable_reasoning: bool = False,
        context_report: dict[str, Any],
    ) -> FinalAnswerModelResult:
        """让真实模型生成最终话术，但安全、低置信、降级和缓存命中保留确定性边界。"""
        skip_reason: str | None = None
        if skip_final_model:
            skip_reason = "runtime_context_direct_answer"
        elif intent == "general_chat" and not citations and not tool_calls:
            skip_reason = "no_business_evidence"
        elif next_action == "ask_clarification":
            skip_reason = "clarification_required"
        elif intent in {"security_request", "low_confidence_query"}:
            skip_reason = "safety_or_low_confidence_boundary"
        elif next_action == "transfer_to_human":
            skip_reason = "evidence_or_business_boundary"
        elif degraded:
            skip_reason = "degraded_path"
        elif cache_hit:
            skip_reason = "common_hit_cache"
        if skip_reason:
            result = FinalAnswerModelResult(answer=answer, fallback_reason=skip_reason)
            trace_store.add(
                request.session_id,
                "model_answer_skipped",
                {"session_id": request.session_id, "intent": intent, "reason": skip_reason},
            )
            return result

        result = self.answer_model_client.compose_answer(
            request=request,
            intent=intent,
            deterministic_answer=answer,
            risk_level=risk_level,
            next_action=next_action,
            tool_calls=tool_calls,
            citations=citations,
            workflow=workflow,
            enable_reasoning=enable_reasoning,
            model_context=context_report["model_context"],
        )
        trace_store.add(
            request.session_id,
            "model_answer_generated",
            {
                "session_id": request.session_id,
                "intent": intent,
                "used_model": result.used_model,
                "model_name": result.model_name,
                "fallback_reason": result.fallback_reason,
            },
        )
        return result

    @staticmethod
    def _apply_route_guard(
        *,
        user_message: str,
        route_result: ModelRouteResult,
    ) -> ModelRouteResult:
        """仅让明确边界覆盖模型，宽泛关键词只用于模型不可用时的 fallback。"""
        guard_intent = classify_guard_intent(user_message)
        if guard_intent is not None and route_result.intent != guard_intent:
            return ModelRouteResult(
                intent=guard_intent,
                candidate=route_result.candidate,
                used_model=route_result.used_model,
                model_name=route_result.model_name,
                fallback_reason=f"rule_guard_{guard_intent}",
                framework=route_result.framework,
                prompt_fragments=route_result.prompt_fragments,
            )
        if guard_intent is not None:
            return route_result

        from rag.domains import infer_public_domains, public_domains
        declared = public_domains(route_result.candidate.knowledge_domains) if route_result.candidate else []
        detected = infer_public_domains(user_message)
        if route_result.intent == "general_chat" and (declared or detected) and not is_runtime_identity_query(user_message):
            return ModelRouteResult(
                intent="faq_query", candidate=route_result.candidate,
                used_model=route_result.used_model, model_name=route_result.model_name,
                fallback_reason="knowledge_evidence_required", framework=route_result.framework,
                prompt_fragments=route_result.prompt_fragments,
            )

        veto_intent = classify_route_veto_intent(user_message, route_result.intent)
        if veto_intent is None:
            return route_result
        return ModelRouteResult(
            intent=veto_intent,
            candidate=route_result.candidate,
            used_model=route_result.used_model,
            model_name=route_result.model_name,
            fallback_reason=f"rule_veto_{route_result.intent}",
            framework=route_result.framework,
            prompt_fragments=route_result.prompt_fragments,
        )

    @observe_operation("resume")
    def resume(self, request: ChatResumeRequest) -> ChatResumeResponse:
        """恢复暂停的 HITL workflow，具体校验和幂等由 workflow 层负责。"""
        return resume_from_checkpoint(request, trace_store)
