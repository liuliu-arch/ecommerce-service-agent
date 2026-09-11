import type {
  AgentCapabilityManifest,
  AgentEndpointKey,
  AgentFeatureKey,
  ChatResponse,
  CostSummary,
  UserMemory,
  WorkflowState,
} from "../types/api";

// 各课后端是独立的课程快照，字段会随课程演进；兼容差异统一收口在这里，相关展示组件只读取稳定语义。
// 这里仅做结构映射和缺失值保留，不根据答案文本猜测业务事实，也不会替旧课程提前开启新能力。

export type ContextObservationKind =
  | "context_summary"
  | "context_builder"
  | "compression"
  | "safety"
  | "prompt_context"
  | "prompt_registry"
  | "rag"
  | "rag_quality";

export type ContextObservation = {
  kind: ContextObservationKind;
  summary: Record<string, unknown>;
};

export type AgentObservation = {
  workflow?: WorkflowState;
  costSummary?: CostSummary;
  runtimeContext?: Record<string, unknown>;
  userMemory?: UserMemory;
  sessionMemory?: Record<string, unknown>;
  contextObservations: ContextObservation[];
  rag?: Record<string, unknown>;
  costRag?: Record<string, unknown>;
  ragHitCount?: number;
  costHitlRequired?: boolean;
};

const FEATURE_ALIASES: Partial<Record<AgentFeatureKey, AgentFeatureKey[]>> = {
  // 部分中期课程沿用 citations，后续课程才统一为 rag_citations；两者表达的是同一项可观察能力。
  rag_citations: ["citations"],
};

export function isAgentFeatureEnabled(capabilities: AgentCapabilityManifest, feature: AgentFeatureKey) {
  if (capabilities.features?.[feature] === true) {
    return true;
  }
  return FEATURE_ALIASES[feature]?.some((alias) => capabilities.features?.[alias] === true) ?? false;
}

export function isAgentEndpointEnabled(capabilities: AgentCapabilityManifest, endpoint: AgentEndpointKey) {
  return capabilities.endpoints?.[endpoint] === true;
}

export function normalizeAgentObservation(response?: ChatResponse): AgentObservation {
  const workflow = resolveWorkflow(response);
  const costSummary = response?.session_state.cost_summary ?? response?.cost_summary;
  const rag = asRecord(response?.session_state.rag);
  const costRag = asRecord(costSummary?.rag);
  const sessionMemory = normalizeSessionMemory(asRecord(response?.session_state.memory));

  return {
    workflow,
    costSummary,
    runtimeContext: resolveRuntimeContext(response),
    userMemory: response?.session_state.user_memory,
    sessionMemory,
    contextObservations: resolveContextObservations(response),
    rag,
    costRag,
    ragHitCount: resolveRagHitCount(response, costSummary),
    costHitlRequired: asBoolean(asRecord(costSummary?.workflow)?.hitl_required),
  };
}

export function resolveWorkflow(response?: ChatResponse) {
  return response?.session_state.workflow ?? response?.workflow ?? undefined;
}

function resolveRuntimeContext(response?: ChatResponse) {
  const direct = asRecord(response?.session_state.runtime_context) ?? asRecord(response?.runtime_context_view);
  if (direct) {
    return direct;
  }

  // Context Builder 会把可信运行时事实放入选中项；这里只读取结构化 facts，不从自然语言 content 反向猜字段。
  const contextReport =
    asRecord(response?.session_state.context_builder) ??
    asRecord(response?.session_state.context_report) ??
    asRecord(response?.context_report);
  const selectedItems = Array.isArray(contextReport?.selected_items) ? contextReport.selected_items : [];
  const runtimeItem = selectedItems
    .map(asRecord)
    .find((item) => item?.source_type === "runtime_context");
  return asRecord(runtimeItem?.facts);
}

function normalizeSessionMemory(memory?: Record<string, unknown>) {
  if (!memory) {
    return undefined;
  }

  const preferences = asRecord(memory.low_risk_preferences);
  return {
    ...memory,
    last_intent: memory.last_intent ?? memory.recent_intent,
    low_risk_preference_summary: preferences
      ? Object.entries(preferences)
          .map(([key, value]) => `${key}=${String(value)}`)
          .join(" / ") || undefined
      : undefined,
  };
}

function resolveContextObservations(response?: ChatResponse) {
  if (!response) {
    return [];
  }

  const state = response.session_state;
  const candidates: Array<[ContextObservationKind, unknown]> = [
    ["context_summary", state.context_summary],
    ["context_builder", state.context_builder ?? state.context_report ?? response.context_report],
    ["compression", state.compression ?? state.compression_report ?? response.compression_report],
    ["safety", state.safety ?? response.safety_decision],
    ["prompt_context", state.prompt_context],
    ["prompt_registry", state.prompt_registry],
    ["rag", state.rag],
    ["rag_quality", state.rag_quality],
  ];
  const seen = new Set<Record<string, unknown>>();
  const observations: ContextObservation[] = [];

  for (const [kind, rawSummary] of candidates) {
    const summary = asRecord(rawSummary);
    if (!summary || seen.has(summary)) {
      continue;
    }
    seen.add(summary);
    observations.push({
      kind,
      summary: kind === "compression" ? normalizeCompression(summary) : kind === "safety" ? normalizeSafety(summary) : summary,
    });
  }
  return observations;
}

function normalizeCompression(summary: Record<string, unknown>) {
  const keptItems = Array.isArray(summary.kept_items) ? summary.kept_items : undefined;
  const droppedItems = Array.isArray(summary.dropped_items) ? summary.dropped_items : undefined;
  return {
    ...summary,
    before: summary.before ?? summary.token_estimate_before,
    after: summary.after ?? summary.token_estimate_after,
    kept_count: summary.kept_count ?? keptItems?.length,
    dropped_count: summary.dropped_count ?? droppedItems?.length,
  };
}

function normalizeSafety(summary: Record<string, unknown>) {
  const sourceScans = Array.isArray(summary.source_scans) ? summary.source_scans : undefined;
  return {
    ...summary,
    tainted_sources:
      summary.tainted_sources ?? sourceScans?.filter((scan) => asRecord(scan)?.tainted === true),
  };
}

function resolveRagHitCount(response?: ChatResponse, costSummary?: CostSummary) {
  const rag = asRecord(response?.session_state.rag);
  const costRag = asRecord(costSummary?.rag);
  const citationCount = response?.citations ? response.citations.length : undefined;

  // 兼容课程递进中的两代字段：早期课程记录 retrieved_count，后期成本治理统一为 rag.hit_count。
  return (
    asNumber(costRag?.hit_count) ??
    asNumber(rag?.hit_count) ??
    response?.session_state.rag_hit_count ??
    asNumber(rag?.retrieved_count) ??
    asNumber(rag?.citation_count) ??
    citationCount
  );
}

function asBoolean(value: unknown) {
  return typeof value === "boolean" ? value : undefined;
}

function asNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function asRecord(value: unknown) {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}
