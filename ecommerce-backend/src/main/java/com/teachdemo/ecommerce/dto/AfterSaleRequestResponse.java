package com.teachdemo.ecommerce.dto;

import java.time.LocalDateTime;

public class AfterSaleRequestResponse {

    private final String requestId;
    private final String orderNo;
    private final String userId;
    private final String requestType;
    private final String reason;
    private final String status;
    private final String approvalId;
    private final LocalDateTime createdAt;
    private final LocalDateTime updatedAt;
    private final String handlingNote;

    public AfterSaleRequestResponse(String requestId, String orderNo, String userId, String requestType,
                                    String reason, String status, String approvalId,
                                    LocalDateTime createdAt, LocalDateTime updatedAt, String handlingNote) {
        this.requestId = requestId;
        this.orderNo = orderNo;
        this.userId = userId;
        this.requestType = requestType;
        this.reason = reason;
        this.status = status;
        this.approvalId = approvalId;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.handlingNote = handlingNote;
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

    public String getRequestType() {
        return requestType;
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

    public String getHandlingNote() {
        return handlingNote;
    }
}
