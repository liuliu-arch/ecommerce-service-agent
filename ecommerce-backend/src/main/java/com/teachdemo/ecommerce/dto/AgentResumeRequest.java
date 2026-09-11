package com.teachdemo.ecommerce.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class AgentResumeRequest {

    @JsonProperty("session_id")
    private final String sessionId;

    @JsonProperty("workflow_id")
    private final String workflowId;

    @JsonProperty("resume_token")
    private final String resumeToken;

    private final String decision;

    @JsonProperty("reviewer_note")
    private final String reviewerNote;

    public AgentResumeRequest(String sessionId, String workflowId, String resumeToken,
                              String decision, String reviewerNote) {
        this.sessionId = sessionId;
        this.workflowId = workflowId;
        this.resumeToken = resumeToken;
        this.decision = decision;
        this.reviewerNote = reviewerNote;
    }

    public String getSessionId() {
        return sessionId;
    }

    public String getWorkflowId() {
        return workflowId;
    }

    public String getResumeToken() {
        return resumeToken;
    }

    public String getDecision() {
        return decision;
    }

    public String getReviewerNote() {
        return reviewerNote;
    }
}
