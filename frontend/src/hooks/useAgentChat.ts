import { useEffect, useMemo, useRef, useState } from "react";

import {
  isAgentEndpointEnabled,
  isAgentFeatureEnabled,
  resolveWorkflow,
} from "../adapters/agentResponseAdapter";
import type {
  AgentCapabilityManifest,
  ChatResponse,
  ChatResumeDecision,
  ChatResumeResponse,
  ConversationMessage,
  DemoUser,
  DemoUserCreatePayload,
  EvalRunResponse,
  FeedbackSubmitResponse,
  ReasoningView,
  RuntimeOrderContextResponse,
  TraceEvent,
} from "../types/api";

const AGENT_BASE_URL = import.meta.env.VITE_AGENT_BASE_URL ?? "http://localhost:8000";
const ECOMMERCE_BASE_URL = import.meta.env.VITE_ECOMMERCE_BASE_URL ?? "http://localhost:8081";

const sessionTokens = new Map<string, string>();
function sessionHeaders(sessionId: string, userId: string): Record<string, string> {
  const token = sessionTokens.get(sessionId) ?? sessionStorage.getItem(`agent-token:${sessionId}`);
  return { "Content-Type": "application/json", "X-User-Id": userId, ...(token ? { "X-Session-Token": token } : {}) };
}
function rememberSessionToken(sessionId: string, response: Response) {
  const token = response.headers.get("X-Session-Token");
  if (token) { sessionTokens.set(sessionId, token); sessionStorage.setItem(`agent-token:${sessionId}`, token); }
}


const DEFAULT_AGENT_CAPABILITIES: AgentCapabilityManifest = {
  schema_version: "agent_capabilities_v1",
  lesson: {
    id: "default-agent",
    title: "默认 Agent",
    summary: "目标 Agent 未提供能力声明时，调试后台只保留最小聊天入口。",
  },
  agent: {
    name: "电商客服 Agent",
    version: "default",
  },
  endpoints: {
    health: true,
    chat: true,
    chat_resume: false,
    trace: false,
    eval_run: false,
  },
  features: {
    chat: true,
    runtime_context: false,
    reasoning_summary: false,
    reasoning_content: false,
    structured_intent: false,
    rag_citations: false,
    tool_calls: false,
    workflow: false,
    human_approval: false,
    memory: false,
    hooks: false,
    trace: false,
    evaluation: false,
    cost_summary: false,
  },
};

const welcomeMessage: ConversationMessage = {
  role: "assistant",
  content: "欢迎来到电商客服 Agent 调试后台。请选择当前课程示例，或输入本课支持的问题观察响应。",
};

const initialConversationMessages: Record<string, ConversationMessage[]> = {};

const initialUsers: DemoUser[] = [
  {
    profile: { userId: "U1001", nickname: "张三", memberLevel: "gold", riskLevel: "low" },
    preferences: {
      userId: "U1001",
      preferredCategories: "耳机,充电器",
      preferredDelivery: "顺丰速运",
      budgetMin: 200,
      budgetMax: 800,
      invoiceRequired: true,
    },
  },
  {
    profile: { userId: "U1002", nickname: "李四", memberLevel: "silver", riskLevel: "low" },
    preferences: {
      userId: "U1002",
      preferredCategories: "音箱,户外数码",
      preferredDelivery: "普通快递",
      budgetMin: 100,
      budgetMax: 500,
      invoiceRequired: false,
    },
  },
  {
    profile: { userId: "U1003", nickname: "王五", memberLevel: "normal", riskLevel: "medium" },
    preferences: {
      userId: "U1003",
      preferredCategories: "",
      preferredDelivery: "",
      budgetMin: null,
      budgetMax: null,
      invoiceRequired: false,
    },
  },
];

type UserConversationState = {
  sessionId: string;
  messages: ConversationMessage[];
  activeResponse?: ChatResponse;
  traceEvents: TraceEvent[];
  resumeResult?: ChatResumeResponse;
};

function createConversationState(userId: string): UserConversationState {
  return {
    sessionId: `session-${userId}-${Math.random().toString(36).slice(2, 10)}`,
    messages: initialConversationMessages[userId]?.map((message) => ({ ...message })) ?? [welcomeMessage],
    traceEvents: [],
  };
}

async function loadCourseRuntimeContext(userId: string): Promise<Record<string, unknown>> {
  try {
    const response = await fetch(
      `${ECOMMERCE_BASE_URL}/api/course-debug/users/${encodeURIComponent(userId)}/order-context`,
    );
    if (!response.ok) {
      return {
        currentPage: "AGENT_WORKBENCH",
        currentUserOrders: [],
        currentUserOrdersTruncated: true,
      };
    }
    const envelope = (await response.json()) as { data?: RuntimeOrderContextResponse };
    if (!envelope.data || !Array.isArray(envelope.data.orders)) {
      return {
        currentPage: "AGENT_WORKBENCH",
        currentUserOrders: [],
        currentUserOrdersTruncated: true,
      };
    }
    return {
      currentPage: "AGENT_WORKBENCH",
      currentUserOrders: envelope.data.orders,
      currentUserOrdersTruncated: envelope.data.truncated === true,
    };
  } catch {
    return {
      currentPage: "AGENT_WORKBENCH",
      currentUserOrders: [],
      currentUserOrdersTruncated: true,
    };
  }
}

export function useAgentChat() {
  const [users, setUsers] = useState<DemoUser[]>(initialUsers);
  const [selectedUserId, setSelectedUserId] = useState(initialUsers[0].profile.userId);
  const [conversationByUser, setConversationByUser] = useState<Record<string, UserConversationState>>(() =>
    Object.fromEntries(
      initialUsers.map((user) => [user.profile.userId, createConversationState(user.profile.userId)]),
    ),
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [evalReport, setEvalReport] = useState<EvalRunResponse | undefined>();
  const [evalError, setEvalError] = useState<string | undefined>();
  const [feedbackReport, setFeedbackReport] = useState<FeedbackSubmitResponse | undefined>();
  const [feedbackError, setFeedbackError] = useState<string | undefined>();
  const [agentCapabilities, setAgentCapabilities] = useState<AgentCapabilityManifest>(DEFAULT_AGENT_CAPABILITIES);
  const [capabilitiesError, setCapabilitiesError] = useState<string | undefined>();
  const isSendingRef = useRef(false);

  const selectedUser = useMemo(
    () => users.find((user) => user.profile.userId === selectedUserId) ?? users[0],
    [selectedUserId, users],
  );
  const activeConversation = conversationByUser[selectedUserId] ?? createConversationState(selectedUserId);

  useEffect(() => {
    let isActive = true;

    async function loadAgentCapabilities() {
      try {
        const response = await fetch(`${AGENT_BASE_URL}/capabilities`);
        if (!response.ok) {
          if (isActive) {
            setAgentCapabilities(DEFAULT_AGENT_CAPABILITIES);
            setCapabilitiesError("目标 Agent 未提供 /capabilities，调试后台只保留最小聊天入口。");
          }
          return;
        }

        const payload = (await response.json()) as AgentCapabilityManifest;
        if (isActive) {
          setAgentCapabilities(payload);
          setCapabilitiesError(undefined);
        }
      } catch {
        if (isActive) {
          setAgentCapabilities(DEFAULT_AGENT_CAPABILITIES);
          setCapabilitiesError("暂时无法读取 /capabilities，调试后台只保留最小聊天入口。");
        }
      }
    }

    void loadAgentCapabilities();

    return () => {
      isActive = false;
    };
  }, []);

  function updateActiveConversation(updater: (current: UserConversationState) => UserConversationState) {
    setConversationByUser((current) => {
      const existing = current[selectedUserId] ?? createConversationState(selectedUserId);
      const next = { ...current, [selectedUserId]: updater(existing) };
      return next;
    });
  }

  function selectUser(userId: string) {
    setSelectedUserId(userId);
    setConversationByUser((current) =>
      current[userId] ? current : persistConversations({ ...current, [userId]: createConversationState(userId) }),
    );
  }

  async function createUser(payload: DemoUserCreatePayload) {
    setIsCreatingUser(true);
    try {
      const response = await fetch(`${ECOMMERCE_BASE_URL}/api/users/demo`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errorPayload = (await response.json().catch(() => undefined)) as { message?: string; detail?: string } | undefined;
        throw new Error(formatErrorDetail(errorPayload?.message ?? errorPayload?.detail));
      }
      const envelope = (await response.json()) as { data: DemoUser };
      const created = envelope.data;
      setUsers((current) => [...current.filter((user) => user.profile.userId !== created.profile.userId), created]);
      setConversationByUser((current) => ({
        ...persistConversations({
          ...current,
          [created.profile.userId]: createConversationState(created.profile.userId),
        }),
      }));
      setSelectedUserId(created.profile.userId);
    } finally {
      setIsCreatingUser(false);
    }
  }

  async function sendMessage(userMessage: string, reasoningView: ReasoningView) {
    if (isSendingRef.current) {
      return;
    }
    if (!isAgentEndpointEnabled(agentCapabilities, "chat")) {
      updateActiveConversation((current) => ({
        ...current,
        messages: [...current.messages, { role: "assistant", content: "当前 Agent 版本未开放 /chat。" }],
      }));
      return;
    }

    isSendingRef.current = true;
    setIsLoading(true);
    const userId = selectedUserId;
    const sessionId = activeConversation.sessionId;
    const effectiveReasoningView =
      reasoningView === "teaching" && !isAgentFeatureEnabled(agentCapabilities, "reasoning_content")
        ? "summary"
        : reasoningView;
    updateActiveConversation((current) => ({
      ...current,
      messages: [...current.messages, { role: "user", content: userMessage }],
    }));

    try {
      // 课程调试后台用安全摘要模拟可信运行时注入；生产商城仍由登录态客服网关构造 Runtime Context。
      const runtimeContext = isAgentFeatureEnabled(agentCapabilities, "runtime_context")
        ? await loadCourseRuntimeContext(userId)
        : undefined;
      const chatResponse = await fetch(`${AGENT_BASE_URL}/chat`, {
        method: "POST",
        headers: sessionHeaders(sessionId, userId),
        body: JSON.stringify({
          session_id: sessionId,
          runtime_user_id: userId,
          runtime_nickname: selectedUser.profile.nickname,
          runtime_member_level: selectedUser.profile.memberLevel,
          runtime_risk_level: selectedUser.profile.riskLevel,
          user_message: userMessage,
          history_messages: activeConversation.messages.map((message) => ({
            role: message.role,
            content: message.content,
          })),
          reasoning_view: effectiveReasoningView,
          debug: true,
          runtime_context: runtimeContext,
        }),
      });

      if (!chatResponse.ok) {
        const errorPayload = (await chatResponse.json().catch(() => undefined)) as { detail?: string } | undefined;
        throw new Error(formatErrorDetail(errorPayload?.detail));
      }

      rememberSessionToken(sessionId, chatResponse);
      const payload = (await chatResponse.json()) as ChatResponse;
      setConversationByUser((current) => {
        const existing = current[userId] ?? createConversationState(userId);
        return persistConversations({
          ...current,
          [userId]: {
            ...existing,
            messages: [...existing.messages, { role: "assistant", content: payload.answer, response: payload }],
            activeResponse: payload,
            resumeResult: undefined,
          },
        });
      });

      await refreshTrace(userId, sessionId);
    } catch (error) {
      setConversationByUser((current) => {
        const existing = current[userId] ?? createConversationState(userId);
        return persistConversations({
          ...current,
          [userId]: {
            ...existing,
            messages: [
              ...existing.messages,
              { role: "assistant", content: error instanceof Error ? error.message : "Agent 请求失败" },
            ],
          },
        });
      });
    } finally {
      isSendingRef.current = false;
      setIsLoading(false);
    }
  }

  async function resumeWorkflow(decision: ChatResumeDecision, reviewerNote: string) {
    const userId = selectedUserId;
    const conversation = conversationByUser[userId];
    const workflow = resolveWorkflow(conversation?.activeResponse);
    if (!isAgentEndpointEnabled(agentCapabilities, "chat_resume") || !isAgentFeatureEnabled(agentCapabilities, "human_approval")) {
      updateActiveConversation((current) => ({
        ...current,
        messages: [...current.messages, { role: "assistant", content: "当前 Agent 版本未开放人工确认恢复。" }],
      }));
      return;
    }
    if (!conversation || !workflow?.workflow_id || !workflow.resume_token) {
      return;
    }

    setIsResuming(true);
    try {
      const resumeResponse = await fetch(`${AGENT_BASE_URL}/chat/resume`, {
        method: "POST",
        headers: sessionHeaders(conversation.sessionId, userId),
        body: JSON.stringify({
          session_id: conversation.sessionId,
          workflow_id: workflow.workflow_id,
          resume_token: workflow.resume_token,
          reviewer_id: "course-reviewer-001",
          reviewer_role: "after_sale_manager",
          decision,
          reviewer_note: reviewerNote,
        }),
      });

      if (!resumeResponse.ok) {
        const errorPayload = (await resumeResponse.json().catch(() => undefined)) as { detail?: string } | undefined;
        throw new Error(formatErrorDetail(errorPayload?.detail));
      }

      const payload = (await resumeResponse.json()) as ChatResumeResponse;
      setConversationByUser((current) => {
        const existing = current[userId] ?? createConversationState(userId);
        const activeResponse =
          existing.activeResponse && payload.session_state
            ? {
                ...existing.activeResponse,
                session_state: { ...existing.activeResponse.session_state, ...payload.session_state },
              }
            : existing.activeResponse;
        return persistConversations({
          ...current,
          [userId]: {
            ...existing,
            activeResponse,
            resumeResult: payload,
            messages: payload.answer
              ? [...existing.messages, { role: "assistant", content: payload.answer }]
              : existing.messages,
          },
        });
      });
      await refreshTrace(userId, conversation.sessionId);
    } catch (error) {
      updateActiveConversation((current) => ({
        ...current,
        messages: [
          ...current.messages,
          { role: "assistant", content: error instanceof Error ? error.message : "审批恢复请求失败" },
        ],
      }));
    } finally {
      setIsResuming(false);
    }
  }

  async function runEval() {
    if (!isAgentEndpointEnabled(agentCapabilities, "eval_run") || !isAgentFeatureEnabled(agentCapabilities, "evaluation")) {
      setEvalReport(undefined);
      setEvalError("当前 Agent 版本未开放 Evaluation。");
      return;
    }

    setIsEvaluating(true);
    setEvalError(undefined);
    try {
      const evalResponse = await fetch(`${AGENT_BASE_URL}/eval/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!evalResponse.ok) {
        const errorPayload = (await evalResponse.json().catch(() => undefined)) as { detail?: string } | undefined;
        throw new Error(formatErrorDetail(errorPayload?.detail));
      }

      setEvalReport((await evalResponse.json()) as EvalRunResponse);
    } catch (error) {
      setEvalError(error instanceof Error ? error.message : "评测运行失败");
    } finally {
      setIsEvaluating(false);
    }
  }

  async function submitFeedback() {
    if (!isAgentFeatureEnabled(agentCapabilities, "feedback_submit")) {
      setFeedbackReport(undefined);
      setFeedbackError("当前 Agent 版本未开放反馈归因。");
      return;
    }

    const userId = selectedUserId;
    const conversation = conversationByUser[userId] ?? createConversationState(userId);
    const observedAnswer =
      conversation.activeResponse?.answer ??
      [...conversation.messages].reverse().find((message) => message.role === "assistant")?.content ??
      "本轮没有可绑定的 Agent 回答。";

    setIsSubmittingFeedback(true);
    setFeedbackError(undefined);
    try {
      const feedbackResponse = await fetch(`${AGENT_BASE_URL}/feedback/submit`, {
        method: "POST",
        headers: sessionHeaders(activeConversation.sessionId, selectedUserId),
        body: JSON.stringify({
          session_id: conversation.sessionId,
          case_id: "unshipped-refund-hitl",
          rating: "negative",
          user_comment: "SO20260601090000008-a1000008 退款时，用户差评说客服没有说明人工审批。",
          observed_answer: observedAnswer,
        }),
      });

      if (!feedbackResponse.ok) {
        const errorPayload = (await feedbackResponse.json().catch(() => undefined)) as { detail?: string } | undefined;
        throw new Error(formatErrorDetail(errorPayload?.detail));
      }

      setFeedbackReport((await feedbackResponse.json()) as FeedbackSubmitResponse);
    } catch (error) {
      setFeedbackError(error instanceof Error ? error.message : "反馈提交失败");
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  async function refreshTrace(userId: string, sessionId: string) {
    if (!isAgentEndpointEnabled(agentCapabilities, "trace") || !isAgentFeatureEnabled(agentCapabilities, "trace")) {
      setConversationByUser((current) => {
        const existing = current[userId] ?? createConversationState(userId);
        return persistConversations({ ...current, [userId]: { ...existing, traceEvents: [] } });
      });
      return;
    }

    const traceResponse = await fetch(`${AGENT_BASE_URL}/sessions/${sessionId}/trace`, { headers: sessionHeaders(sessionId, userId) });
    if (traceResponse.ok) {
      const traces = (await traceResponse.json()) as TraceEvent[];
      setConversationByUser((current) => {
        const existing = current[userId] ?? createConversationState(userId);
        return persistConversations({ ...current, [userId]: { ...existing, traceEvents: traces } });
      });
    }
  }

  return {
    users,
    selectedUser,
    selectedUserId,
    messages: activeConversation.messages,
    isLoading,
    isResuming,
    isEvaluating,
    isSubmittingFeedback,
    isCreatingUser,
    activeResponse: activeConversation.activeResponse,
    traceEvents: activeConversation.traceEvents,
    evalReport,
    evalError,
    feedbackReport,
    feedbackError,
    resumeResult: activeConversation.resumeResult,
    agentBaseUrl: AGENT_BASE_URL,
    agentCapabilities,
    capabilitiesError,
    selectUser,
    createUser,
    sendMessage,
    resumeWorkflow,
    runEval,
    submitFeedback,
  };
}

function persistConversations(conversations: Record<string, UserConversationState>) {
  return conversations;
}

function formatErrorDetail(detail: unknown) {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (detail) {
    return JSON.stringify(detail);
  }
  return "Agent 请求失败";
}
