export type Citation = {
  citation_id?: string;
  source?: string;
  source_title?: string;
  source_path?: string;
  chunk_id?: string;
  title?: string;
  snippet: string;
  score?: number;
  retrieval_stage?: "pre_retrieval" | "tool_retrieval" | null;
  metadata?: Record<string, unknown> | null;
};

export type ToolActionTrace = {
  tool_name: string;
  arguments: Record<string, unknown>;
  reason?: string;
};

export type ToolObservationTrace = {
  tool_name?: string;
  status: "success" | "error" | "skipped" | string;
  summary: string;
  data?: Record<string, unknown>;
  facts?: Record<string, unknown>;
  omitted_fields?: string[];
  next_action?: string | null;
  error_category?: string | null;
};

export type ToolCallTrace = {
  tool_name?: string;
  arguments?: Record<string, unknown>;
  output_summary?: string;
  status?: "success" | "error" | "skipped" | string;
  action?: ToolActionTrace;
  observation?: ToolObservationTrace;
  attempts?: number;
  tool_source?: "function" | "mcp" | "preload" | null;
  risk_level?: "low" | "medium" | "high" | null;
  needs_human_approval?: boolean | null;
  next_action?: string | null;
  error_type?: string | null;
  candidates?: Array<Record<string, unknown>>;
  clarification_field?: string | null;
  clarification_prompt?: string | null;
};

export type AgentMode = "teaching_rule_react" | "production_react" | "langchain_react";
export type ReasoningView = "off" | "summary" | "teaching";

export type AgentFeatureKey =
  | "after_sale_assessment"
  | "basic_rag"
  | "business_fact_recheck"
  | "chat"
  | "chat_resume"
  | "checkpoint"
  | "citations"
  | "common_hit_cache"
  | "context_builder"
  | "context_compression"
  | "context_relevance"
  | "cost_governance"
  | "cost_summary"
  | "degradation"
  | "document_chunking"
  | "eval_case_backfill"
  | "eval_report"
  | "evaluation"
  | "fact_conflict_resolution"
  | "failure_attribution"
  | "feedback_submit"
  | "fixed_cases"
  | "frozen_fields"
  | "grounded_model_answer"
  | "hidden_cot_protection"
  | "high_risk_action_boundary"
  | "hitl_pending_approval"
  | "hooks"
  | "human_approval"
  | "hybrid_rag"
  | "idempotency"
  | "keyword_retrieval"
  | "langgraph_stategraph"
  | "light_heavy_path"
  | "llm_final_answer"
  | "llm_intent_router"
  | "local_model_messages"
  | "low_confidence_fallback"
  | "mcp"
  | "mcp_prompts"
  | "mcp_resources"
  | "mcp_tools"
  | "memory"
  | "memory_exclusion"
  | "memory_write_policy"
  | "needs_human_approval"
  | "next_action"
  | "observation_compression"
  | "permission_check"
  | "pre_retrieval"
  | "privacy_redaction"
  | "prompt_injection_defense"
  | "public_safety_summary"
  | "public_trace_schema"
  | "query_rewrite"
  | "rag_citations"
  | "rag_index_cache"
  | "rag_quality_check"
  | "real_llm_answer"
  | "real_llm_calling"
  | "realtime_business_facts"
  | "reasoning_content"
  | "reasoning_summary"
  | "received_return_workflow"
  | "reranker"
  | "risk_level"
  | "route_plan"
  | "route_planner"
  | "runtime_context"
  | "runtime_context_dual_channel"
  | "safe_trace_summary"
  | "session_memory"
  | "sliding_window"
  | "source_trust_level"
  | "structured_intent"
  | "taint_marking"
  | "tool_calling"
  | "tool_calls"
  | "tool_candidates"
  | "tool_clarification"
  | "tool_observation"
  | "tool_rag_joint_answer"
  | "tool_schema"
  | "trace"
  | "unshipped_refund_workflow"
  | "vector_retrieval"
  | "workflow";

export type AgentEndpointKey = "health" | "chat" | "chat_resume" | "trace" | "eval_run";

export type AgentCapabilityManifest = {
  schema_version: "agent_capabilities_v1" | string;
  lesson?: {
    id?: string;
    number?: number;
    title?: string;
    summary?: string;
  };
  agent?: {
    name?: string;
    version?: string;
  };
  endpoints?: Partial<Record<AgentEndpointKey, boolean>>;
  features?: Partial<Record<AgentFeatureKey, boolean>>;
  disabled_reasons?: Partial<Record<AgentFeatureKey | AgentEndpointKey, string>>;
};

export type TraceEvent = {
  event_type: string;
  timestamp: string;
  agent_mode?: AgentMode | null;
  step?: number | null;
  schema_version?: string | null;
  category?: string | null;
  stage?: string | null;
  name?: string | null;
  status?: string | null;
  target?: Record<string, unknown> | null;
  ids?: Record<string, unknown> | null;
  summary?: Record<string, unknown> | null;
  signals?: string[] | null;
  safety?: Record<string, unknown> | null;
  payload: Record<string, unknown>;
};

export type HookEvent = {
  hook_type?: string;
  target_name?: string;
  action?: string;
  result?: string;
  reason?: string;
  safe_summary?: Record<string, unknown>;
  redacted?: boolean;
  degraded?: boolean;
  event_type?: string;
  timestamp?: string;
  stage?: string;
  status?: string;
  target?: Record<string, unknown> | null;
  summary?: Record<string, unknown> | null;
  payload?: Record<string, unknown>;
};

export type WorkflowNode = {
  node: string;
  status?: string | null;
  pending_action?: string | null;
};

export type WorkflowState = {
  workflow_id?: string | null;
  workflow_type?: string | null;
  agent_mode?: AgentMode | string | null;
  runtime_user_id?: string | null;
  current_node?: string | null;
  status?: string | null;
  pending_action?: string | null;
  risk_summary?: string | null;
  resume_token?: string | null;
  order_no?: string | null;
  order_id?: string | null;
  order_status?: string | null;
  payment_status?: string | null;
  logistics_status?: string | null;
  approval_id?: string | null;
  idempotency_key?: string | null;
  frozen_fields?: Record<string, unknown>;
  node_history?: WorkflowNode[];
  approval?: ApprovalState | null;
};

export type ApprovalState = {
  workflow_id?: string | null;
  decision?: "approved" | "rejected" | "needs_more_info" | string | null;
  status?: string | null;
  business_request_id?: string | null;
  next_action?: string | null;
  reviewer_note_provided?: boolean | null;
  boundary?: string | null;
  tool_name?: string | null;
  tool_status?: string | null;
  error?: string | null;
};

export type CostSummary = {
  schema_version?: "cost_summary_v1" | string;
  cost_profile?: string;
  path_type?: string;
  agent_mode?: AgentMode | string;
  model_calls?: Record<string, number>;
  tool_call_count?: number;
  business_tool_call_count?: number;
  rag?: Record<string, unknown>;
  tokens?: Record<string, number>;
  prompt_fragments?: Record<string, unknown>;
  prompt_tokens?: number;
  answer_tokens?: number;
  total_tokens?: number;
  context_chars?: number;
  token_source?: string;
  estimated_total_cost_cny?: number;
  reasoning?: Record<string, unknown>;
  workflow?: Record<string, unknown>;
  limits?: Record<string, unknown>;
  degradation?: Record<string, unknown>;
  safety_boundary?: Record<string, unknown>;
};

export type ContextSummary = {
  schema_version?: string;
  total_estimated_tokens?: number;
  has_budget_warning?: boolean;
  sources?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

export type ChatResponse = {
  session_id: string;
  answer: string;
  intent?: string;
  intent_result?: Record<string, unknown>;
  route_plan?: Record<string, unknown> | null;
  planner_trace?: Record<string, unknown> | null;
  citations?: Citation[];
  tool_calls?: ToolCallTrace[];
  clarification?: Record<string, unknown> | null;
  next_action?: string | null;
  risk_level?: "low" | "medium" | "high" | string;
  needs_human_approval?: boolean;
  degraded?: boolean;
  hook_events?: HookEvent[];
  hook_completion?: Record<string, unknown>;
  mcp_context?: Record<string, unknown>;
  cost_summary?: CostSummary;
  workflow?: WorkflowState | null;
  runtime_context_view?: Record<string, unknown>;
  context_report?: Record<string, unknown>;
  compression_report?: Record<string, unknown>;
  safety_decision?: Record<string, unknown>;
  reasoning_summary: string[];
  reasoning_content?: string | null;
  session_state: {
    message_count: number;
    intent?: string;
    intent_result?: Record<string, unknown>;
    next_action?: string | null;
    risk_level?: "low" | "medium" | "high" | string;
    needs_human_approval?: boolean;
    degraded?: boolean;
    agent_mode?: AgentMode;
    tool_source?: "function" | "mcp";
    reasoning_view?: ReasoningView;
    react_steps?: number;
    route_plan?: Record<string, unknown> | null;
    planner_trace?: Record<string, unknown> | null;
    rag_hit_count?: number;
    route_plan_confidence?: number | null;
    rag_retrieval_paths?: string[];
    runtime_context?: Record<string, unknown>;
    user_memory?: UserMemory;
    memory?: Record<string, unknown>;
    workflow?: WorkflowState;
    approval?: ApprovalState;
    clarification?: Record<string, unknown>;
    runtime_clarification?: Record<string, unknown>;
    context_summary?: ContextSummary;
    context_builder?: Record<string, unknown>;
    context_report?: Record<string, unknown>;
    compression?: Record<string, unknown>;
    compression_report?: Record<string, unknown>;
    safety?: Record<string, unknown>;
    prompt_context?: Record<string, unknown> | null;
    prompt_registry?: Record<string, unknown>;
    rag?: Record<string, unknown>;
    rag_quality?: Record<string, unknown>;
    cost_summary?: CostSummary;
    cost_observation?: Record<string, unknown>;
    model?: Record<string, unknown>;
    model_answer?: Record<string, unknown>;
    trace?: Record<string, unknown>;
    next_gap?: string;
    prompt_security?: Record<string, unknown>;
    business_facts?: Record<string, unknown>;
    tool_calling?: Record<string, unknown>;
    tool_rag?: Record<string, unknown>;
    degradation?: Record<string, unknown>;
    mcp?: Record<string, unknown>;
    mcp_context?: Record<string, unknown>;
    hook_events?: HookEvent[];
    hook_completion?: Record<string, unknown>;
  };
};

export type UserProfile = {
  userId: string;
  nickname: string;
  memberLevel: string;
  riskLevel: string;
};

export type UserPreferences = {
  userId: string;
  preferredCategories?: string | null;
  preferredDelivery?: string | null;
  budgetMin?: number | null;
  budgetMax?: number | null;
  invoiceRequired?: boolean | null;
};

export type DemoUser = {
  profile: UserProfile;
  preferences: UserPreferences;
};

export type RuntimeOrderSummary = {
  orderNo: string;
  status: string;
  paymentStatus?: string | null;
  fulfillmentStatus?: string | null;
  totalAmount?: number | null;
  createdAt?: string | null;
  paidAt?: string | null;
  shippedAt?: string | null;
  deliveredAt?: string | null;
  logisticsNo?: string | null;
  itemSummary: string[];
  items: Array<{
    productName: string;
    quantity: number;
    returnable: boolean | null;
  }>;
  returnable: boolean | null;
};

export type RuntimeOrderContextResponse = {
  orders: RuntimeOrderSummary[];
  truncated: boolean;
  limit: number;
};

export type DemoUserCreatePayload = {
  userId: string;
  nickname: string;
  memberLevel: string;
  riskLevel: string;
  preferredCategories?: string;
  preferredDelivery?: string;
  budgetMin?: number;
  budgetMax?: number;
  invoiceRequired?: boolean;
};

export type UserMemory = {
  status?: string;
  source?: string;
  preferences?: Partial<Omit<UserPreferences, "userId">> & Record<string, unknown>;
  error?: string;
};

export type ChatResumeDecision = "approved" | "rejected" | "needs_more_info";

export type ChatResumeResponse = {
  session_id: string;
  workflow_id: string;
  status:
    | "approval_resumed"
    | "approval_rejected"
    | "approval_needs_more_info"
    | "invalid_resume_token"
    | "not_found"
    | "not_paused"
    | "resume_failed";
  message: string;
  workflow?: WorkflowState | null;
  answer?: string | null;
  session_state?: {
    approval?: ApprovalState;
    workflow?: WorkflowState;
  } | null;
};

export type EvalCaseResult = {
  case_id: string;
  passed: boolean;
  user_message: string;
  expected_signals: string[];
  actual_answer: string;
  actual_tools: string[];
  missing_signals: string[];
  actual_citations?: string[];
  actual_trace_events?: string[];
  missing_tools?: string[];
  unexpected_tools?: string[];
  missing_citations?: string[];
  missing_trace_events?: string[];
  missing_session_state?: string[];
  forbidden_text_hits?: string[];
  failure_categories?: string[];
};

export type EvalRunResponse = {
  total: number;
  passed: number;
  failed: number;
  summary: Record<string, unknown>;
  results: EvalCaseResult[];
};

export type FeedbackSubmitResponse = {
  record: {
    feedback_id: string;
    session_id: string;
    case_id?: string | null;
    rating: string;
    trace_event_names: string[];
    eval_failure_categories: string[];
    attributions: Array<{
      module: string;
      category: string;
      evidence: string[];
      suggested_fix: string;
    }>;
    backfilled_case: Record<string, unknown>;
  };
  eval_report?: EvalRunResponse | null;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
};
