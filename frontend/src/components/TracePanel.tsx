import { useState } from "react";

import {
  isAgentEndpointEnabled,
  isAgentFeatureEnabled,
  normalizeAgentObservation,
  type AgentObservation,
  type ContextObservationKind,
} from "../adapters/agentResponseAdapter";
import type {
  AgentCapabilityManifest,
  AgentEndpointKey,
  AgentFeatureKey,
  ChatResumeDecision,
  ChatResumeResponse,
  ChatResponse,
  CostSummary,
  HookEvent,
  ReasoningView,
  ToolCallTrace,
  TraceEvent,
  WorkflowState,
} from "../types/api";

type LearningToggles = {
  tools: boolean;
  rag: boolean;
  reasoning: boolean;
};

type TracePanelProps = {
  response?: ChatResponse;
  traces: TraceEvent[];
  selectedReasoningView: ReasoningView;
  toggles: LearningToggles;
  resumeResult?: ChatResumeResponse;
  isResuming: boolean;
  isChatLoading: boolean;
  capabilities: AgentCapabilityManifest;
  onClarificationCandidateSelect: (candidateValue: string) => void | Promise<void>;
  onResumeWorkflow: (decision: ChatResumeDecision, reviewerNote: string) => Promise<void>;
};

type ClarificationCandidateView = {
  value: string;
  label: string;
  hint?: string;
};

export function TracePanel({
  response,
  traces,
  selectedReasoningView,
  toggles,
  resumeResult,
  isResuming,
  isChatLoading,
  capabilities,
  onClarificationCandidateSelect,
  onResumeWorkflow,
}: TracePanelProps) {
  const [reviewerNote, setReviewerNote] = useState("课程演示：人工确认后提交模拟业务申请");
  const reasoningView = selectedReasoningView;
  const visibleTraces = traces.slice(-10);
  const hookEvents = [
    ...traces.filter((trace) => trace.event_type === "hook_executed"),
    ...(response?.session_state.hook_events ?? response?.hook_events ?? []),
  ].slice(-5);
  const traceStartTime = visibleTraces[0] ? new Date(visibleTraces[0].timestamp).getTime() : undefined;
  const reasoningTitle = reasoningView === "teaching" ? "Reasoning 过程" : "执行摘要";
  const reasoningItems = response?.reasoning_summary ?? [];
  const observation = normalizeAgentObservation(response);
  const { workflow, costSummary, runtimeContext, userMemory, sessionMemory, contextObservations } = observation;
  const canResume =
    isAgentFeatureEnabled(capabilities, "human_approval") &&
    isAgentEndpointEnabled(capabilities, "chat_resume") &&
    workflow?.status === "paused" &&
    (workflow.pending_action === "require_approval" || workflow.pending_action === "require_human_approval") &&
    Boolean(workflow.resume_token);

  return (
    <aside className="panel trace-panel">
      <div className="panel-header">
        <span>生产行为观察台</span>
      </div>

      {reasoningView !== "off" ? (
        <div className="trace-section">
          <h3>{reasoningTitle}</h3>
          {response && reasoningView === "teaching" ? (
            <div className="trace-card">
              <strong>教学执行链路</strong>
              <span>这里先展示后端整理的意图、工具、Observation 和答案组织摘要；下面会展示本轮模型返回的 reasoning_content。</span>
            </div>
          ) : null}
          <ul>
            {!response ? <li>等待对话开始</li> : null}
            {response && !reasoningItems.length ? <li>本轮没有生成执行摘要</li> : null}
            {reasoningItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {toggles.reasoning ? (
        <div className="trace-section">
          <h3>模型 reasoning_content</h3>
          <div className={`trace-card reasoning-content${response?.reasoning_content ? "" : " muted"}`}>
            <strong>调试后台展示的模型思考内容</strong>
            <span>
              {response?.reasoning_content ??
                (response
                  ? "本轮没有拿到 reasoning_content。可能是当前路径未返回、模型或平台不支持 thinking/reasoning_content，或后端模型配置不可用。"
                  : "发送问题后，这里会展示模型返回的 reasoning_content。")}
            </span>
            <small>课程环境使用测试数据，可以把它作为 CoT/Reasoning 教学素材；真实客服终端通常改为展示脱敏摘要和 trace，避免暴露内部规则、未验证假设、工具细节或用户敏感信息。</small>
          </div>
        </div>
      ) : null}

      <ToolSection
        response={response}
        visible={toggles.tools || toggles.reasoning}
        available={isAgentFeatureEnabled(capabilities, "tool_calls")}
        disabledReason={disabledReason(capabilities, "tool_calls")}
        isChatLoading={isChatLoading}
        onClarificationCandidateSelect={onClarificationCandidateSelect}
      />
      <RealtimeFactsSection
        response={response}
        available={isAgentFeatureEnabled(capabilities, "realtime_business_facts")}
      />
      <DecisionBoundarySection response={response} />
      <ModelUsageSection response={response} costSummary={costSummary} />
      <RagSection
        response={response}
        observation={observation}
        visible={toggles.rag}
        available={isAgentFeatureEnabled(capabilities, "rag_citations")}
        disabledReason={disabledReason(capabilities, "rag_citations")}
      />
      <ToolRagSection
        response={response}
        available={isAgentFeatureEnabled(capabilities, "tool_rag_joint_answer")}
        disabledReason={disabledReason(capabilities, "tool_rag_joint_answer")}
      />
      <McpSection
        response={response}
        available={
          isAgentFeatureEnabled(capabilities, "mcp") ||
          isAgentFeatureEnabled(capabilities, "mcp_tools") ||
          isAgentFeatureEnabled(capabilities, "mcp_resources") ||
          isAgentFeatureEnabled(capabilities, "mcp_prompts")
        }
        disabledReason={disabledReason(capabilities, "mcp")}
      />
      <RuntimeContextSection runtimeContext={runtimeContext} hasResponse={Boolean(response)} />
      <MemorySection
        userMemory={userMemory}
        sessionMemory={sessionMemory}
        available={isAgentFeatureEnabled(capabilities, "memory")}
        disabledReason={disabledReason(capabilities, "memory")}
      />
      <WorkflowSection
        workflow={workflow}
        available={isAgentFeatureEnabled(capabilities, "workflow")}
        disabledReason={disabledReason(capabilities, "workflow")}
      />
      <ApprovalSection
        workflow={workflow}
        canResume={canResume}
        reviewerNote={reviewerNote}
        isResuming={isResuming}
        resumeResult={resumeResult}
        available={isAgentFeatureEnabled(capabilities, "human_approval") && isAgentEndpointEnabled(capabilities, "chat_resume")}
        disabledReason={disabledReason(capabilities, "human_approval")}
        onReviewerNoteChange={setReviewerNote}
        onResumeWorkflow={onResumeWorkflow}
      />
      <CostSection
        costSummary={costSummary}
        ragHitCount={observation.ragHitCount}
        hitlRequired={observation.costHitlRequired}
        available={isAgentFeatureEnabled(capabilities, "cost_summary")}
        disabledReason={disabledReason(capabilities, "cost_summary")}
      />
      <HookSection
        events={hookEvents}
        completion={response?.session_state.hook_completion ?? response?.hook_completion}
        available={isAgentFeatureEnabled(capabilities, "hooks")}
        disabledReason={disabledReason(capabilities, "hooks")}
      />
      {contextObservations.map(({ kind, summary }) => (
        <ContextSection key={kind} kind={kind} summary={summary} />
      ))}
      <TraceSection
        traces={visibleTraces}
        traceStartTime={traceStartTime}
        traceSummary={asRecord(response?.session_state.trace)}
        available={isAgentFeatureEnabled(capabilities, "trace") && isAgentEndpointEnabled(capabilities, "trace")}
        disabledReason={disabledReason(capabilities, "trace")}
      />
    </aside>
  );
}

function RuntimeContextSection({
  runtimeContext,
  hasResponse,
}: {
  runtimeContext?: Record<string, unknown>;
  hasResponse: boolean;
}) {
  if (!runtimeContext) {
    return (
      <div className="trace-section">
        <h3>Runtime Context</h3>
        <div className="trace-card muted">
          {hasResponse ? "当前响应未单独返回公开 Runtime Context 摘要。" : "等待本次请求的 Runtime Context。"}
        </div>
      </div>
    );
  }

  const trusted = asRecord(runtimeContext.trusted_for_model);
  const systemOnly = asRecord(runtimeContext.system_only);
  const pageContext = asRecord(trusted?.page_context);
  const permissionDecision = asRecord(runtimeContext.permission_decision);

  return (
    <div className="trace-section">
      <h3>Runtime Context</h3>
      <div className="trace-card">
        <MetaList
          items={[
            ["用户", runtimeContext.user_id || systemOnly?.user_id],
            ["昵称", runtimeContext.nickname || trusted?.nickname],
            ["会员", runtimeContext.member_level || trusted?.member_level],
            ["风险", runtimeContext.risk_level || systemOnly?.risk_level],
            ["请求", runtimeContext.request_id],
            ["租户", runtimeContext.tenant_id],
            ["店铺", runtimeContext.shop_id],
            ["渠道", runtimeContext.channel],
            ["权限", listValue(runtimeContext.permissions || systemOnly?.permissions)],
            ["风险策略", runtimeContext.risk_policy],
            ["Debug", listValue(runtimeContext.debug_flags)],
            ["页面订单", pageContext?.current_order_id],
            ["权限结论", permissionDecision?.allowed === false ? "拒绝" : permissionDecision?.allowed === true ? "通过" : undefined],
          ]}
        />
        {Array.isArray(runtimeContext.conflict_notes) && runtimeContext.conflict_notes.length ? (
          <span>{runtimeContext.conflict_notes.join("；")}</span>
        ) : null}
      </div>
    </div>
  );
}

function MemorySection({
  userMemory,
  sessionMemory,
  available,
  disabledReason,
}: {
  userMemory?: ChatResponse["session_state"]["user_memory"];
  sessionMemory?: Record<string, unknown>;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  const preferences = userMemory?.preferences ?? {};

  return (
    <div className="trace-section">
      <h3>Memory</h3>
      <div className="trace-card">
        <div className="card-title-row">
          <strong>User Memory</strong>
          <Badge tone={userMemory?.status === "available" ? "ok" : "neutral"}>{userMemory?.status || "empty"}</Badge>
        </div>
        <MetaList
          items={[
            ["品类", preferences.preferredCategories],
            ["配送", preferences.preferredDelivery],
            ["预算", budgetValue(preferences.budgetMin, preferences.budgetMax)],
            ["发票", boolLabel(preferences.invoiceRequired)],
          ]}
        />
      </div>
      <div className="trace-card">
        <strong>Session Memory</strong>
        <MetaList
          items={[
            ["意图", sessionMemory?.last_intent],
            ["低风险偏好", sessionMemory?.low_risk_preference_summary],
            ["商品", sessionMemory?.last_product_name || sessionMemory?.last_product_id],
            ["订单", sessionMemory?.last_order_no || sessionMemory?.last_order_id],
            ["售后", sessionMemory?.last_after_sale_request_id],
            ["退款", sessionMemory?.last_refund_request_id],
            ["审批", sessionMemory?.last_approval_id],
            ["注入历史", sessionMemory?.history_injected_message_count],
            ["裁剪历史", sessionMemory?.history_trimmed_message_count],
          ]}
        />
      </div>
    </div>
  );
}

function ToolSection({
  response,
  visible,
  available,
  disabledReason,
  isChatLoading,
  onClarificationCandidateSelect,
}: {
  response?: ChatResponse;
  visible: boolean;
  available: boolean;
  disabledReason?: string;
  isChatLoading: boolean;
  onClarificationCandidateSelect: (candidateValue: string) => void | Promise<void>;
}) {
  if (!visible) {
    return null;
  }
  if (!available) {
    return <DisabledFeatureSection title="本轮工具调用" reason={disabledReason} />;
  }

  const toolCalling = asRecord(response?.session_state.tool_calling);
  const clarificationPlan = asRecord(toolCalling?.["clarification_plan"]);
  const plannerError = asRecord(toolCalling?.["planner_error"]);

  return (
    <div className="trace-section">
      <h3>本轮工具调用</h3>
      {plannerError ? (
        <div className="trace-card">
          <div className="card-title-row">
            <strong>LLM 澄清规划</strong>
            <Badge tone="warn">blocked</Badge>
          </div>
          <span>{stringValue(plannerError.message) || "模型规划不可用，本轮不会回退到规则路径。"}</span>
          <MetaList
            items={[
              ["来源", plannerError.source],
              ["回退", plannerError.fallback],
            ]}
          />
        </div>
      ) : null}
      {response?.clarification ? (
        <div className="trace-card">
          <div className="card-title-row">
            <strong>{response.tool_calls?.length ? "工具后澄清" : "工具调用前澄清"}</strong>
            <Badge tone="warn">ask</Badge>
          </div>
          <span>{stringValue(response.clarification.message) || "需要补充工具参数。"}</span>
          <MetaList
            items={[
              ["规划来源", clarificationPlan?.source],
              ["模型", clarificationPlan?.model_name],
              ["规划工具", clarificationPlan?.tool_name],
              ["缺失字段", listValue(clarificationPlan?.missing_required)],
              ["澄清字段", response.clarification.clarification_field],
              ["候选数量", Array.isArray(response.clarification.candidates) ? String(response.clarification.candidates.length) : undefined],
            ]}
          />
          <ClarificationCandidateActions
            candidates={clarificationCandidates(response.clarification)}
            disabled={isChatLoading}
            onSelect={onClarificationCandidateSelect}
          />
        </div>
      ) : null}
      {response?.tool_calls?.length ? (
        response.tool_calls.map((call, callIndex) => (
          <div className="trace-card" key={`${toolCallName(call)}-${toolCallStatus(call)}-${callIndex}`}>
            <div className="card-title-row">
              <strong>{toolCallName(call)}</strong>
              <Badge tone={toolCallStatus(call) === "success" ? "ok" : "warn"}>{toolCallStatus(call)}</Badge>
            </div>
            <span>{toolCallSummary(call)}</span>
            <MetaList
              items={[
                ["来源", call.tool_source],
                ["参数", compactJson(toolCallArguments(call))],
                ["尝试次数", numberValue(call.attempts)],
                ["风险", call.risk_level],
                ["需要人工", call.needs_human_approval === true ? "是" : call.needs_human_approval === false ? "否" : undefined],
                ["下一步", call.next_action ?? call.observation?.next_action],
                ["错误类型", call.error_type ?? call.observation?.error_category ?? stringValue(call.observation?.facts?.error_category)],
                ["省略字段", listValue(call.observation?.omitted_fields)],
                ["澄清字段", call.clarification_field],
                ["候选数量", call.candidates?.length ? String(call.candidates.length) : undefined],
              ]}
            />
          </div>
        ))
      ) : (
        <div className="trace-card muted">当前对话还没有调用业务工具</div>
      )}
    </div>
  );
}

function RealtimeFactsSection({ response, available }: { response?: ChatResponse; available: boolean }) {
  const businessFacts = response?.session_state.business_facts;
  if (!available || !businessFacts) {
    return null;
  }

  const need = asRecord(businessFacts.need);
  const result = asRecord(businessFacts.result);

  return (
    <div className="trace-section">
      <h3>实时事实</h3>
      <div className="trace-card">
        <div className="card-title-row">
          <strong>{stringValue(need?.kind) || "business_facts"}</strong>
          <Badge tone={result?.found === false ? "warn" : "ok"}>{result?.found === false ? "missing" : "found"}</Badge>
        </div>
        <span>{stringValue(result?.summary) || stringValue(need?.reason) || "等待实时事实查询结果。"}</span>
        <MetaList
          items={[
            ["订单", need?.order_id],
            ["SKU", need?.sku],
            ["实时查询", boolLabel(need?.requires_realtime)],
            ["用户匹配", boolLabel(result?.user_matched)],
          ]}
        />
      </div>
    </div>
  );
}

function DecisionBoundarySection({ response }: { response?: ChatResponse }) {
  if (!response) {
    return null;
  }
  const routePlan = asRecord(response.route_plan) ?? asRecord(response.session_state.route_plan);
  const intentResult = asRecord(response.intent_result) ?? asRecord(response.session_state.intent_result);
  const nextAction = response.next_action ?? response.session_state.next_action;
  const intent = response.intent ?? response.session_state.intent ?? stringValue(routePlan?.intent) ?? stringValue(intentResult?.intent);
  const riskLevel = response.risk_level ?? response.session_state.risk_level;
  const needsHumanApproval = response.needs_human_approval ?? response.session_state.needs_human_approval;
  const degraded = response.degraded ?? response.session_state.degraded;
  const shouldShow =
    nextAction ||
    intent ||
    riskLevel ||
    typeof needsHumanApproval === "boolean" ||
    typeof degraded === "boolean" ||
    routePlan ||
    intentResult ||
    response.session_state.degradation;

  if (!shouldShow) {
    return null;
  }

  const degradation = response.session_state.degradation ?? {};

  return (
    <div className="trace-section">
      <h3>处理边界</h3>
      <div className="trace-card">
        <MetaList
          items={[
            ["下一步", nextAction],
            ["意图", intent],
            ["风险", riskLevel],
            ["需要人工", boolLabel(needsHumanApproval)],
            ["降级", boolLabel(degraded)],
            ["错误分类", degradation.error_category],
          ]}
        />
        {stringValue(degradation.fallback_message) ? <span>{stringValue(degradation.fallback_message)}</span> : null}
      </div>
    </div>
  );
}

function ModelUsageSection({ response, costSummary }: { response?: ChatResponse; costSummary?: CostSummary }) {
  if (!response) {
    return null;
  }

  const model = asRecord(response.session_state.model);
  const routePlanner = asRecord(model?.route_planner);
  const routeCandidate = asRecord(routePlanner?.candidate);
  const modelAnswer = asRecord(response.session_state.model_answer);
  const finalAnswer = asRecord(model?.final_answer) ?? modelAnswer;
  const modelCalls = costSummary?.model_calls;
  const routePlan = asRecord(response.route_plan) ?? asRecord(response.session_state.route_plan);
  const plannerTrace = asRecord(response.planner_trace) ?? asRecord(response.session_state.planner_trace);
  const hasModelSignal = routePlanner || finalAnswer || modelCalls || routePlan?.source || plannerTrace || modelAnswer;

  if (!hasModelSignal) {
    return null;
  }

  return (
    <div className="trace-section">
      <h3>模型使用</h3>
      <div className="trace-card">
        <MetaList
          items={[
            ["路由模型", boolLabel(routePlanner?.used_model)],
            ["结构化候选通过校验", boolLabel(routePlanner?.candidate_validated)],
            ["候选已进入最终计划", boolLabel(routePlanner?.candidate_applied)],
            ["模型候选工具", listValue(routeCandidate?.required_tools)],
            ["模型候选知识域", listValue(routeCandidate?.knowledge_domains)],
            ["路由兜底", routePlanner?.fallback_reason],
            ["最终回答模型", boolLabel(finalAnswer?.used_model)],
            ["最终回答兜底", finalAnswer?.fallback_reason],
            ["Planner 来源", routePlan?.source],
            ["服务端约束", listValue(routePlan?.policy_constraints)],
            ["模型调用", numberValue(modelCallCount(modelCalls ?? {}))],
          ]}
        />
        <small>这里只展示模型是否参与、走了哪条兜底路径和公开调用计数，不展示隐藏 Prompt 或内部推理链。</small>
      </div>
    </div>
  );
}

function RagSection({
  response,
  observation,
  visible,
  available,
  disabledReason,
}: {
  response?: ChatResponse;
  observation: AgentObservation;
  visible: boolean;
  available: boolean;
  disabledReason?: string;
}) {
  if (!visible) {
    return null;
  }
  if (!available) {
    return <DisabledFeatureSection title="RAG 引用" reason={disabledReason} />;
  }

  const { rag, costRag, ragHitCount: hitCount } = observation;
  const hasRagSummary = rag || costRag || hitCount !== undefined;

  return (
    <div className="trace-section">
      <h3>RAG 引用</h3>
      {hasRagSummary ? (
        <div className="trace-card">
          <MetaList
            items={[
              ["低置信", boolLabel(rag?.low_confidence)],
              ["命中数", numberValue(hitCount)],
            ]}
          />
        </div>
      ) : null}
      {response?.citations?.length ? (
        response.citations.map((citation, citationIndex) => (
          <div
            className="trace-card"
            key={`${citationSource(citation)}-${citation.retrieval_stage ?? "unknown"}-${citationIndex}`}
          >
            <strong>{citation.title ?? citation.source_title ?? citation.chunk_id ?? "知识引用"}</strong>
            <span>{citation.snippet}</span>
            <small>{citationMeta(citation)}</small>
          </div>
        ))
      ) : (
        <div className="trace-card muted">本轮还没有命中知识库引用</div>
      )}
    </div>
  );
}

function ToolRagSection({
  response,
  available,
  disabledReason,
}: {
  response?: ChatResponse;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  const toolRag = asRecord(response?.session_state.tool_rag);
  if (!toolRag) {
    return (
      <div className="trace-section">
        <h3>Tool + RAG 来源合成</h3>
        <div className="trace-card muted">等待商品工具与知识库引用合成结果。</div>
      </div>
    );
  }

  const observation = asRecord(toolRag.tool_observation);
  const observationFacts = asRecord(observation?.facts);
  const toolAction = asRecord(toolRag.tool_action);

  return (
    <div className="trace-section">
      <h3>Tool + RAG 来源合成</h3>
      <div className="trace-card">
        <div className="card-title-row">
          <strong>{stringValue(toolAction?.tool_name) || "tool_rag_joint_answer"}</strong>
          <Badge tone="ok">grounded</Badge>
        </div>
        <MetaList
          items={[
            ["答案来源", listValue(toolRag.answer_sources)],
            ["引用片段", listValue(toolRag.citation_chunk_ids)],
            ["工具动作", toolAction?.tool_name],
            ["Observation", observation?.summary],
            ["SKU", observationFacts?.sku],
            ["库存", observationFacts?.inventory ?? observationFacts?.stock],
            ["价格", observationFacts?.price],
            ["活动价", observationFacts?.promotion_price],
          ]}
        />
        <small>实时库存价格来自业务工具；卖点、活动和售后口径来自 RAG citation。</small>
      </div>
    </div>
  );
}

function McpSection({
  response,
  available,
  disabledReason,
}: {
  response?: ChatResponse;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  const mcpContext = asRecord(response?.mcp_context) ?? asRecord(response?.session_state.mcp_context) ?? asRecord(response?.session_state.mcp);
  if (!mcpContext) {
    return (
      <div className="trace-section">
        <h3>MCP 工具目录</h3>
        <div className="trace-card muted">等待 MCP 工具、资源和 Prompt 绑定信息。</div>
      </div>
    );
  }

  return (
    <div className="trace-section">
      <h3>MCP 工具目录</h3>
      <div className="trace-card">
        <div className="card-title-row">
          <strong>{stringValue(mcpContext.selected_tool) || "mcp_context"}</strong>
          <Badge tone="neutral">{stringValue(mcpContext.tool_source) || "mcp"}</Badge>
        </div>
        <MetaList
          items={[
            ["工具来源", mcpContext.tool_source],
            ["选中工具", mcpContext.selected_tool],
            ["工具数", numberValue(asNumber(mcpContext.tool_count))],
            ["候选工具", listValue(mcpContext.available_tools || mcpContext.tool_names || mcpContext.tools)],
            ["资源", listValue(mcpContext.resources)],
            ["Prompt", listValue(mcpContext.prompts)],
            ["参数校验", mcpContext.argument_validation],
          ]}
        />
        <small>MCP 提供工具说明、资源和 Prompt 绑定；参数治理、业务读取和 Observation 仍由 Tool Use 链路负责。</small>
      </div>
    </div>
  );
}

function WorkflowSection({
  workflow,
  available,
  disabledReason,
}: {
  workflow?: WorkflowState;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  if (!workflow) {
    return (
      <div className="trace-section">
        <h3>LangGraph 节点流</h3>
        <div className="trace-card muted">普通问题未进入复杂售后工作流。</div>
      </div>
    );
  }

  const frozenFields = asRecord(workflow.frozen_fields);
  const orderId = workflow.order_no ?? workflow.order_id ?? stringValue(frozenFields?.order_id);

  return (
    <div className="trace-section">
      <h3>LangGraph 节点流</h3>
      <div className="trace-card">
        <div className="card-title-row">
          <strong>{workflow.workflow_type || "after_sale_workflow"}</strong>
          <Badge tone={workflow.status === "paused" ? "warn" : workflow.status === "completed" ? "ok" : "neutral"}>
            {workflow.status || "unknown"}
          </Badge>
        </div>
          <MetaList
            items={[
              ["订单", orderId],
              ["当前节点", workflow.current_node],
              ["下一步", workflow.pending_action],
              ["工作流", workflow.workflow_id],
            ]}
          />
        {workflow.risk_summary ? <span>{workflow.risk_summary}</span> : null}
      </div>
      {workflow.node_history?.length ? (
        <div className="node-flow">
          {workflow.node_history.map((rawNode, index) => {
            const node = typeof rawNode === "string" ? { node: rawNode, status: "completed" } : rawNode;
            return (
            <div className="node-pill" key={`${node.node}-${index}`}>
              <strong>{node.node}</strong>
              <small>
                {node.status || "completed"}
                {node.pending_action ? ` · ${node.pending_action}` : ""}
              </small>
            </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function ApprovalSection({
  workflow,
  canResume,
  reviewerNote,
  isResuming,
  resumeResult,
  available,
  disabledReason,
  onReviewerNoteChange,
  onResumeWorkflow,
}: {
  workflow?: WorkflowState;
  canResume: boolean;
  reviewerNote: string;
  isResuming: boolean;
  resumeResult?: ChatResumeResponse;
  available: boolean;
  disabledReason?: string;
  onReviewerNoteChange: (note: string) => void;
  onResumeWorkflow: (decision: ChatResumeDecision, reviewerNote: string) => Promise<void>;
}) {
  if (!available) {
    return null;
  }

  if (!workflow && !resumeResult) {
    return null;
  }

  return (
    <div className="trace-section">
      <h3>人工确认</h3>
      {canResume ? (
        <div className="trace-card approval-card">
          <strong>待人工确认：{workflow?.pending_action}</strong>
          <span>
            请先核对这次暂停的订单和售后状态；审批通过后也只是提交模拟退款 / 售后申请，不代表真实资金或仓储动作完成。
          </span>
          <MetaList
            items={[
              ["订单号", workflow?.order_no ?? workflow?.order_id],
              ["退款人ID", workflow?.runtime_user_id ?? asRecord(workflow?.frozen_fields)?.runtime_user_id],
              ["售后类型", workflowTypeLabel(workflow?.workflow_type)],
              ["订单状态", orderStatusLabel(workflow?.order_status ?? stringValue(asRecord(workflow?.frozen_fields)?.order_status))],
              ["支付状态", paymentStatusLabel(workflow?.payment_status)],
              ["物流状态", orderStatusLabel(workflow?.logistics_status ?? stringValue(asRecord(workflow?.frozen_fields)?.logistics_status))],
              ["风险说明", workflow?.risk_summary],
              ["workflow_id", workflow?.workflow_id],
              ["resume_token", maskToken(workflow?.resume_token)],
            ]}
          />
          <textarea value={reviewerNote} onChange={(event) => onReviewerNoteChange(event.target.value)} rows={3} />
          <div className="approval-actions">
            <button type="button" disabled={isResuming} onClick={() => onResumeWorkflow("approved", reviewerNote)}>
              批准
            </button>
            <button type="button" disabled={isResuming} onClick={() => onResumeWorkflow("rejected", reviewerNote)}>
              拒绝
            </button>
            <button type="button" disabled={isResuming} onClick={() => onResumeWorkflow("needs_more_info", reviewerNote)}>
              补充信息
            </button>
          </div>
        </div>
      ) : (
        <div className="trace-card muted">当前没有可恢复的待处理审批。</div>
      )}
      {resumeResult ? (
        <div className="trace-card">
          <div className="card-title-row">
            <strong>恢复结果</strong>
            <Badge tone={resumeResult.status === "approval_resumed" ? "ok" : "warn"}>{resumeResult.status}</Badge>
          </div>
          <span>{resumeResult.message}</span>
          <MetaList
            items={[
              ["业务申请", resumeResult.session_state?.approval?.business_request_id],
              ["下一步", resumeResult.session_state?.approval?.next_action],
              ["边界", resumeResult.session_state?.approval?.boundary],
            ]}
          />
        </div>
      ) : null}
    </div>
  );
}

function CostSection({
  costSummary,
  ragHitCount,
  hitlRequired,
  available,
  disabledReason,
}: {
  costSummary?: CostSummary;
  ragHitCount?: number;
  hitlRequired?: boolean;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  if (!costSummary) {
    return (
      <div className="trace-section">
        <h3>成本摘要</h3>
        <div className="trace-card muted">等待本次请求的 cost_summary。</div>
      </div>
    );
  }

  const tokens = costSummary.tokens ?? {};
  const degradation = costSummary.degradation ?? {};
  const modelCalls = costSummary.model_calls ?? {};
  const totalTokens = asNumber(tokens.total_estimated) ?? asNumber(costSummary.total_tokens);
  const modelCallTotal = modelCallCount(modelCalls);
  const warnings = listValue(degradation.warnings);

  return (
    <div className="trace-section">
      <h3>成本摘要</h3>
      <div className="metric-grid">
        <Metric label="路径" value={costSummary.path_type} />
        <Metric label="模型调用" value={numberValue(modelCallTotal)} />
        <Metric label="工具调用" value={numberValue(costSummary.tool_call_count)} />
        <Metric label="RAG 命中" value={numberValue(ragHitCount)} />
        <Metric label="Token 估算" value={numberValue(totalTokens)} />
        <Metric label="HITL" value={boolLabel(hitlRequired)} />
      </div>
      {warnings ? (
      <div className="trace-card">
        <MetaList
          items={[
            ["告警", warnings],
          ]}
        />
        <small>这里是课程项目的单次请求估算，不是模型服务商账单、预算审批或 FinOps 平台。</small>
      </div>
      ) : null}
    </div>
  );
}

function HookSection({
  events,
  completion,
  available,
  disabledReason,
}: {
  events: Array<TraceEvent | HookEvent>;
  completion?: Record<string, unknown>;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  return (
    <div className="trace-section">
      <h3>Hook 事件</h3>
      {completion ? (
        <div className="trace-card">
          <div className="card-title-row">
            <strong>on_completion</strong>
            <Badge tone={completion.degraded_count ? "warn" : "ok"}>summary</Badge>
          </div>
          <MetaList
            items={[
              ["Hook 数", numberValue(asNumber(completion.hook_count))],
              ["工具数", numberValue(asNumber(completion.tool_count))],
              ["工具", listValue(completion.touched_tools)],
              ["脱敏", numberValue(asNumber(completion.redacted_count))],
              ["降级", numberValue(asNumber(completion.degraded_count))],
              ["风险命中", numberValue(asNumber(completion.risk_hit_count))],
            ]}
          />
        </div>
      ) : null}
      {events.length ? (
        events.map((trace) => (
          <div className="trace-card" key={hookEventKey(trace)}>
            <div className="card-title-row">
              <strong>{hookEventTitle(trace)}</strong>
              <Badge tone={hookEventStatus(trace) === "success" || hookEventStatus(trace) === "recorded" ? "ok" : "neutral"}>
                {hookEventStatus(trace)}
              </Badge>
            </div>
            <MetaList
              items={[
                ["目标", hookEventTarget(trace)],
                ["动作", hookEventAction(trace)],
                ["脱敏", boolLabel(hookEventSummary(trace).redacted ?? hookEventRedacted(trace))],
                ["降级", boolLabel(hookEventSummary(trace).degraded ?? hookEventDegraded(trace))],
                ["原因", hookEventReason(trace)],
              ]}
            />
          </div>
        ))
      ) : (
        <div className="trace-card muted">当前 trace 中还没有 hook_executed 事件。</div>
      )}
    </div>
  );
}

function ContextSection({
  kind,
  summary,
}: {
  kind: ContextObservationKind;
  summary?: Record<string, unknown>;
}) {
  if (!summary) {
    return null;
  }

  const selectedItems = Array.isArray(summary.selected_items) ? summary.selected_items : undefined;
  const excludedItems = Array.isArray(summary.excluded_items) ? summary.excluded_items : undefined;
  const conflictResolutions = Array.isArray(summary.conflict_resolutions) ? summary.conflict_resolutions : undefined;
  const taintedSources = Array.isArray(summary.tainted_sources) ? summary.tainted_sources : undefined;
  const rewrite = asRecord(summary.rewrite);
  const plan = asRecord(summary.plan);
  const index = asRecord(summary.index);
  const cache = asRecord(summary.cache);
  const isContextBuilder = Boolean(selectedItems || excludedItems || conflictResolutions);
  const isCompression = summary.before !== undefined || summary.after !== undefined || summary.kept_count !== undefined;
  const isSafety = summary.blocked_user_request !== undefined || taintedSources;
  const isPromptContext = summary.document_count !== undefined || summary.conflict_count !== undefined;
  const isPromptRegistry = summary.selected_fragment_ids !== undefined || summary.disabled_fragment_ids !== undefined;
  const isRagQuality = kind === "rag_quality";
  const isIndexCache = Boolean(index || cache);
  const ragMode = stringValue(summary.mode);
  const isRag =
    summary.matched_snippet_ids !== undefined ||
    summary.matched_chunk_ids !== undefined ||
    summary.matched_sections !== undefined ||
    summary.confidence_level !== undefined ||
    rewrite !== undefined ||
    plan !== undefined ||
    index !== undefined ||
    cache !== undefined ||
    Boolean(ragMode && /(rag|retrieval|chunking|rerank|hybrid|cache)/i.test(ragMode));
  const title = isContextBuilder
    ? "Context Builder"
    : isCompression
      ? "上下文压缩"
      : isSafety
        ? "安全上下文"
        : isPromptRegistry
          ? "Prompt Registry"
          : isRagQuality
            ? "RAG 质量检查"
          : isRag
            ? "RAG 检索"
            : isPromptContext
              ? "Prompt Context"
              : "上下文摘要";
  const sourcePreview = selectedItems
    ?.map((item) => {
      const record = asRecord(item);
      return [record?.source_type, record?.trust_level].filter(Boolean).join(":");
    })
    .filter(Boolean)
    .slice(0, 4)
    .join(" / ");
  const taintPreview = taintedSources
    ?.map((item) => {
      const record = asRecord(item);
      return [record?.source_type, listValue(record?.categories)].filter(Boolean).join(":");
    })
    .filter(Boolean)
    .slice(0, 3)
    .join(" / ");

  return (
    <div className="trace-section">
      <h3>{title}</h3>
      <div className="trace-card">
        <MetaList
          items={[
            ["估算 token", numberValue(asNumber(summary.total_estimated_tokens))],
            ["预算告警", boolLabel(summary.has_budget_warning)],
            ["来源数", Array.isArray(summary.sources) ? String(summary.sources.length) : undefined],
            ["选中片段", selectedItems ? String(selectedItems.length) : undefined],
            ["排除片段", excludedItems ? String(excludedItems.length) : undefined],
            ["冲突处理", conflictResolutions ? String(conflictResolutions.length) : undefined],
            ["压缩前", numberValue(asNumber(summary.before))],
            ["压缩后", numberValue(asNumber(summary.after))],
            ["保留片段", numberValue(asNumber(summary.kept_count))],
            ["丢弃片段", numberValue(asNumber(summary.dropped_count))],
            ["阻断请求", boolLabel(summary.blocked_user_request)],
            ["拒绝主题", listValue(summary.refused_topics)],
            ["污染来源", taintedSources ? String(taintedSources.length) : undefined],
            ["已脱敏", boolLabel(summary.redaction_applied)],
            ["模式", summary.mode],
            ["文档数", numberValue(asNumber(summary.document_count))],
            ["冲突数", numberValue(asNumber(summary.conflict_count))],
            ["估算 Prompt token", numberValue(asNumber(summary.estimated_prompt_tokens))],
            ["选中片段", listValue(summary.selected_fragment_ids)],
            ["关闭片段", listValue(summary.disabled_fragment_ids)],
            ["命中片段", listValue(summary.matched_snippet_ids || summary.matched_chunk_ids)],
            ["命中章节", listValue(summary.matched_sections)],
            ["原始问题", rewrite?.original_query || plan?.original_query],
            ["检索改写", isIndexCache ? undefined : rewrite?.rewritten_query || plan?.rewritten_query],
            ["改写原因", isIndexCache ? undefined : rewrite?.reason || plan?.reason],
            ["补充词", isIndexCache ? undefined : listValue(rewrite?.added_terms)],
            ["检索场景", plan?.scene],
            ["允许主题", listValue(plan?.allowed_topics)],
            ["关键词", isIndexCache ? undefined : listValue(plan?.keyword_terms)],
            ["候选片段", listValue(summary.candidate_chunk_ids)],
            ["重排后", listValue(summary.reranked_chunk_ids)],
            ["选中知识", listValue(summary.selected_chunk_ids)],
            ["重排模式", summary.rerank_mode],
            ["重排模型", summary.rerank_model],
            ["向量命中", isIndexCache ? undefined : listValue(summary.vector_chunk_ids)],
            ["关键词命中", isIndexCache ? undefined : listValue(summary.keyword_chunk_ids)],
            ["初始 Top", summary.initial_top_chunk_id || summary.raw_top_chunk_id],
            ["索引版本", index?.version],
            ["索引片段", numberValue(asNumber(index?.chunk_count))],
            ["缓存命中", boolLabel(cache?.cache_hit)],
            ["可缓存", boolLabel(cache?.cacheable)],
            ["缓存范围", cache?.scope],
            ["置信度", summary.confidence_level],
            ["低置信动作", summary.low_confidence_action],
            ["实时缺口", boolLabel(summary.realtime_gap)],
            ["评测用例", numberValue(asNumber(summary.case_count))],
            ["通过用例", numberValue(asNumber(summary.passed_cases))],
            ["平均 Recall@K", numberValue(asNumber(summary.average_recall_at_k))],
            ["平均 Precision@K", numberValue(asNumber(summary.average_precision_at_k))],
          ]}
        />
        {sourcePreview ? <span>{sourcePreview}</span> : null}
        {conflictResolutions?.length ? <small>{String(conflictResolutions[0])}</small> : null}
        {taintPreview ? <span>{taintPreview}</span> : null}
        <small>这里只展示上下文来源、压缩和安全摘要，不展示敏感原文。</small>
      </div>
    </div>
  );
}

function TraceSection({
  traces,
  traceStartTime,
  traceSummary,
  available,
  disabledReason,
}: {
  traces: TraceEvent[];
  traceStartTime?: number;
  traceSummary?: Record<string, unknown>;
  available: boolean;
  disabledReason?: string;
}) {
  if (!available) {
    return null;
  }

  return (
    <div className="trace-section">
      <h3>轨迹事件</h3>
      {traceSummary ? (
        <div className="trace-card">
          <MetaList
            items={[
              ["事件数", numberValue(asNumber(traceSummary.event_count))],
              ["公开 Trace", boolLabel(traceSummary.public_trace_only)],
              ["隐藏 CoT 暴露", boolLabel(traceSummary.hidden_cot_exposed)],
            ]}
          />
        </div>
      ) : null}
      {traces.length ? (
        traces.map((trace) => (
          <div className="trace-card" key={`${trace.timestamp}-${trace.event_type}`}>
            <div className="card-title-row">
              <strong>{trace.step ? `Step ${trace.step} · ${trace.event_type}` : trace.event_type}</strong>
              <Badge tone={trace.category === "hitl" || trace.status === "warning" ? "warn" : "neutral"}>
                {trace.category || "system"}
              </Badge>
            </div>
            <MetaList
              items={[
                ["阶段", trace.stage],
                ["状态", trace.status],
                ["耗时", formatTraceElapsed(trace.timestamp, traceStartTime)],
                ["信号", trace.signals?.slice(0, 4).join(" / ")],
              ]}
            />
            {trace.safety?.payload_sanitized ? <small>payload 已做公开展示脱敏。</small> : null}
          </div>
        ))
      ) : (
        <div className="trace-card muted">等待生成轨迹</div>
      )}
    </div>
  );
}

function DisabledFeatureSection({ title, reason }: { title: string; reason?: string }) {
  return (
    <div className="trace-section capability-disabled">
      <h3>{title}</h3>
      <div className="trace-card muted">
        <strong>当前版本未开放</strong>
        <span>{reason || "目标 Agent 的能力配置中没有开放这个功能。"}</span>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="metric-card">
      <small>{label}</small>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function Badge({ children, tone }: { children: string; tone: "ok" | "warn" | "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function ClarificationCandidateActions({
  candidates,
  disabled,
  onSelect,
}: {
  candidates: ClarificationCandidateView[];
  disabled: boolean;
  onSelect: (candidateValue: string) => void | Promise<void>;
}) {
  if (!candidates.length) {
    return null;
  }

  return (
    <div className="candidate-options" aria-label="澄清候选">
      {candidates.map((candidate) => (
        <button
          type="button"
          className="candidate-option"
          key={candidate.value}
          disabled={disabled}
          onClick={() => onSelect(candidate.value)}
        >
          <strong>{candidate.label}</strong>
          {candidate.hint ? <small>{candidate.hint}</small> : null}
        </button>
      ))}
    </div>
  );
}

function MetaList({ items }: { items: Array<[string, unknown]> }) {
  const visibleItems = items.filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!visibleItems.length) {
    return null;
  }

  return (
    <dl className="meta-list">
      {visibleItems.map(([label, value]) => (
        <div key={`${label}-${String(value)}`}>
          <dt>{label}</dt>
          <dd>{String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function disabledReason(capabilities: AgentCapabilityManifest, key: AgentFeatureKey | AgentEndpointKey) {
  return capabilities.disabled_reasons?.[key];
}

function formatTraceElapsed(timestamp: string, startTime?: number) {
  if (!startTime) {
    return "+0ms";
  }

  const elapsed = Math.max(0, new Date(timestamp).getTime() - startTime);
  if (elapsed < 1000) {
    return `+${elapsed}ms`;
  }

  return `+${(elapsed / 1000).toFixed(1)}s`;
}

function maskToken(token?: string | null) {
  if (!token) {
    return undefined;
  }
  if (token.length <= 10) {
    return token;
  }
  return `${token.slice(0, 7)}...${token.slice(-4)}`;
}

function workflowTypeLabel(type?: string | null) {
  const labels: Record<string, string> = {
    refund_before_shipping: "未发货退款",
    return_after_delivery: "签收后退货",
    unknown: "售后类型待确认",
  };
  return type ? labels[type] ?? type : undefined;
}

function orderStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    PENDING_PAYMENT: "待支付",
    PAID: "已支付",
    PENDING_SHIPMENT: "待发货",
    PAID_PENDING_SHIPMENT: "待发货",
    SHIPPED: "已发货",
    DELIVERED: "已签收",
    CANCELLED: "已取消",
    REFUNDING: "退款处理中",
    REFUNDED: "已退款",
  };
  return status ? labels[status] ?? status : undefined;
}

function paymentStatusLabel(status?: string | null) {
  const labels: Record<string, string> = {
    UNPAID: "未支付",
    PAID: "已支付",
    REFUNDING: "退款处理中",
    REFUNDED: "已退款",
  };
  return status ? labels[status] ?? status : undefined;
}

function numberValue(value?: number) {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : undefined;
}

function modelCallCount(modelCalls: Record<string, number>) {
  const explicitTotal = asNumber(modelCalls.total_estimated) ?? asNumber(modelCalls.total);
  if (explicitTotal !== undefined) {
    return explicitTotal;
  }

  const values = Object.entries(modelCalls)
    .filter(([key]) => key !== "total_estimated" && key !== "total")
    .map(([, value]) => value)
    .filter((value) => typeof value === "number" && Number.isFinite(value));
  return values.length ? values.reduce((sum, value) => sum + value, 0) : undefined;
}

function asNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function boolLabel(value: unknown) {
  if (typeof value !== "boolean") {
    return undefined;
  }
  return value ? "是" : "否";
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function listValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.length ? value.join(" / ") : undefined;
  }
  return stringValue(value);
}

function asRecord(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}

function clarificationCandidates(clarification: Record<string, unknown> | null | undefined): ClarificationCandidateView[] {
  const rawCandidates = clarification?.candidates;
  if (!Array.isArray(rawCandidates)) {
    return [];
  }

  return rawCandidates
    .map((candidate) => {
      if (typeof candidate === "string") {
        return { value: candidate, label: candidate };
      }
      const record = asRecord(candidate);
      const value = stringValue(record?.value) ?? stringValue(record?.order_id) ?? stringValue(record?.id);
      if (!value) {
        return undefined;
      }
      return {
        value,
        label: stringValue(record?.label) ?? value,
        hint: stringValue(record?.hint) ?? stringValue(record?.summary) ?? stringValue(record?.description),
      };
    })
    .filter((candidate): candidate is ClarificationCandidateView => Boolean(candidate));
}

function compactJson(value: unknown) {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  return JSON.stringify(value);
}

function toolCallName(call: ToolCallTrace) {
  return call.tool_name ?? call.action?.tool_name ?? call.observation?.tool_name ?? "tool_call";
}

function toolCallStatus(call: ToolCallTrace) {
  return call.status ?? call.observation?.status ?? "unknown";
}

function toolCallSummary(call: ToolCallTrace) {
  return call.output_summary ?? call.observation?.summary ?? "工具返回了结构化结果。";
}

function toolCallArguments(call: ToolCallTrace) {
  return call.arguments ?? call.action?.arguments;
}

function citationSource(citation: NonNullable<ChatResponse["citations"]>[number]) {
  return citation.source ?? citation.source_path ?? citation.chunk_id ?? "unknown";
}

function citationMeta(citation: NonNullable<ChatResponse["citations"]>[number]) {
  return [
    citationSource(citation),
    typeof citation.score === "number" && Number.isFinite(citation.score) ? `score ${citation.score.toFixed(2)}` : undefined,
    citation.retrieval_stage,
  ]
    .filter(Boolean)
    .join(" · ");
}

function hookEventSummary(event: TraceEvent | HookEvent) {
  if ("safe_summary" in event && event.safe_summary) {
    return event.safe_summary;
  }
  return event.summary ?? event.payload ?? {};
}

function hookEventKey(event: TraceEvent | HookEvent) {
  return `${event.timestamp ?? "chat-response"}-${hookEventTitle(event)}-${hookEventTarget(event) ?? ""}-${hookEventAction(event) ?? ""}`;
}

function hookEventTitle(event: TraceEvent | HookEvent) {
  return stringValue(("hook_type" in event ? event.hook_type : undefined) || event.summary?.hook_type || event.stage || event.event_type) ?? "hook";
}

function hookEventStatus(event: TraceEvent | HookEvent) {
  return stringValue(event.status || ("result" in event ? event.result : undefined)) ?? "recorded";
}

function hookEventTarget(event: TraceEvent | HookEvent) {
  return stringValue(("target_name" in event ? event.target_name : undefined) || event.target?.name || event.payload?.tool_name || event.payload?.target_name);
}

function hookEventAction(event: TraceEvent | HookEvent) {
  return stringValue(("action" in event ? event.action : undefined) || event.summary?.action || event.payload?.action);
}

function hookEventReason(event: TraceEvent | HookEvent) {
  return stringValue("reason" in event ? event.reason : undefined);
}

function hookEventRedacted(event: TraceEvent | HookEvent) {
  return "redacted" in event ? event.redacted : undefined;
}

function hookEventDegraded(event: TraceEvent | HookEvent) {
  return "degraded" in event ? event.degraded : undefined;
}

function budgetValue(min: unknown, max: unknown) {
  const minNumber = asNumber(min);
  const maxNumber = asNumber(max);
  if (typeof minNumber === "number" && typeof maxNumber === "number") {
    return `${minNumber}-${maxNumber}`;
  }
  if (typeof minNumber === "number") {
    return `${minNumber}+`;
  }
  if (typeof maxNumber === "number") {
    return `<=${maxNumber}`;
  }
  return undefined;
}
