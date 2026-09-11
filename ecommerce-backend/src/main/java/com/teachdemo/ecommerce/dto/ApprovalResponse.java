package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class ApprovalResponse {

    private final String approvalId;
    private final String businessType;
    private final String businessId;
    private final String riskLevel;
    private final BigDecimal amount;
    private final String status;
    private final String operator;
    private final String comment;
    private final LocalDateTime createdAt;
    private final LocalDateTime approvedAt;

    public ApprovalResponse(String approvalId, String businessType, String businessId, String riskLevel,
                            BigDecimal amount, String status, String operator, String comment,
                            LocalDateTime createdAt, LocalDateTime approvedAt) {
        this.approvalId = approvalId;
        this.businessType = businessType;
        this.businessId = businessId;
        this.riskLevel = riskLevel;
        this.amount = amount;
        this.status = status;
        this.operator = operator;
        this.comment = comment;
        this.createdAt = createdAt;
        this.approvedAt = approvedAt;
    }

    public String getApprovalId() {
        return approvalId;
    }

    public String getBusinessType() {
        return businessType;
    }

    public String getBusinessId() {
        return businessId;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public String getStatus() {
        return status;
    }

    public String getOperator() {
        return operator;
    }

    public String getComment() {
        return comment;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getApprovedAt() {
        return approvedAt;
    }
}
