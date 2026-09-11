package com.teachdemo.ecommerce.dto;

import jakarta.validation.constraints.NotBlank;

public class CustomerServiceResumeRequest {

    @NotBlank
    private String sessionId;

    @NotBlank
    private String resumeToken;

    @NotBlank
    private String decision;

    private String relatedOrderNo;

    private String relatedAfterSaleNo;

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public String getResumeToken() {
        return resumeToken;
    }

    public void setResumeToken(String resumeToken) {
        this.resumeToken = resumeToken;
    }

    public String getDecision() {
        return decision;
    }

    public void setDecision(String decision) {
        this.decision = decision;
    }

    public String getRelatedOrderNo() {
        return relatedOrderNo;
    }

    public void setRelatedOrderNo(String relatedOrderNo) {
        this.relatedOrderNo = relatedOrderNo;
    }

    public String getRelatedAfterSaleNo() {
        return relatedAfterSaleNo;
    }

    public void setRelatedAfterSaleNo(String relatedAfterSaleNo) {
        this.relatedAfterSaleNo = relatedAfterSaleNo;
    }
}
