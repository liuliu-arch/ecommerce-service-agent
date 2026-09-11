package com.teachdemo.ecommerce.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

public class AgentChatRequest {

    @JsonProperty("session_id")
    private final String sessionId;

    @JsonProperty("runtime_user_id")
    private final String runtimeUserId;

    @JsonProperty("runtime_nickname")
    private final String runtimeNickname;

    @JsonProperty("runtime_member_level")
    private final String runtimeMemberLevel;

    @JsonProperty("runtime_risk_level")
    private final String runtimeRiskLevel;

    @JsonProperty("user_message")
    private final String userMessage;

    @JsonProperty("agent_mode")
    private final String agentMode = "production_react";

    @JsonProperty("reasoning_view")
    private final String reasoningView = "off";

    private final boolean debug = false;

    @JsonProperty("runtime_context")
    private final Map<String, Object> runtimeContext;

    public AgentChatRequest(String sessionId, String runtimeUserId, String runtimeNickname,
                            String runtimeMemberLevel, String runtimeRiskLevel, String userMessage,
                            Map<String, Object> runtimeContext) {
        this.sessionId = sessionId;
        this.runtimeUserId = runtimeUserId;
        this.runtimeNickname = runtimeNickname;
        this.runtimeMemberLevel = runtimeMemberLevel;
        this.runtimeRiskLevel = runtimeRiskLevel;
        this.userMessage = userMessage;
        this.runtimeContext = runtimeContext;
    }

    public String getSessionId() {
        return sessionId;
    }

    public String getRuntimeUserId() {
        return runtimeUserId;
    }

    public String getRuntimeNickname() {
        return runtimeNickname;
    }

    public String getRuntimeMemberLevel() {
        return runtimeMemberLevel;
    }

    public String getRuntimeRiskLevel() {
        return runtimeRiskLevel;
    }

    public String getUserMessage() {
        return userMessage;
    }

    public String getAgentMode() {
        return agentMode;
    }

    public String getReasoningView() {
        return reasoningView;
    }

    public boolean isDebug() {
        return debug;
    }

    public Map<String, Object> getRuntimeContext() {
        return runtimeContext;
    }
}
