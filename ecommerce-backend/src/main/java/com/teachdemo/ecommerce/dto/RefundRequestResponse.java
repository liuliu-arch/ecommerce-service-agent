package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class RefundRequestResponse {

    private final String requestId;
    private final String orderNo;
    private final String userId;
    private final BigDecimal amount;
    private final String reason;
    private final String status;
    private final String approvalId;
    private final LocalDateTime createdAt;
    private final LocalDateTime updatedAt;

    public RefundRequestResponse(String requestId, String orderNo, String userId, BigDecimal amount,
                                 String reason, String status, String approvalId,
                                 LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.requestId = requestId;
        this.orderNo = orderNo;
        this.userId = userId;
        this.amount = amount;
        this.reason = reason;
        this.status = status;
        this.approvalId = approvalId;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public String getRequestId() {
        return requestId;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public String getUserId() {
        return userId;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public String getReason() {
        return reason;
    }

    public String getStatus() {
        return status;
    }

    public String getApprovalId() {
        return approvalId;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
}
