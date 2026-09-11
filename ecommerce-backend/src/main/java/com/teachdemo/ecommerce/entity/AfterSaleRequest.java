package com.teachdemo.ecommerce.entity;

import java.time.LocalDateTime;
import java.math.BigDecimal;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class AfterSaleRequest {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String requestId;

    private String orderNo;

    private String userId;

    private String requestType;

    private String reason;

    private String status;

    private BigDecimal amount;

    private Boolean userConfirmed;

    private String approvalId;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    private String handlingNote;

    protected AfterSaleRequest() {
    }

    public AfterSaleRequest(String requestId, String orderNo, String userId, String requestType,
                            String reason, String status, String approvalId,
                            LocalDateTime createdAt, LocalDateTime updatedAt, String handlingNote) {
        this.requestId = requestId;
        this.orderNo = orderNo;
        this.userId = userId;
        this.requestType = requestType;
        this.reason = reason;
        this.status = status;
        this.amount = null;
        this.userConfirmed = true;
        this.approvalId = approvalId;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.handlingNote = handlingNote;
    }

    public AfterSaleRequest(String requestId, String orderNo, String userId, String requestType,
                            String reason, String status, BigDecimal amount, Boolean userConfirmed,
                            LocalDateTime createdAt, LocalDateTime updatedAt, String handlingNote) {
        this.requestId = requestId;
        this.orderNo = orderNo;
        this.userId = userId;
        this.requestType = requestType;
        this.reason = reason;
        this.status = status;
        this.amount = amount;
        this.userConfirmed = userConfirmed;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.handlingNote = handlingNote;
    }

    public Long getId() {
        return id;
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

    public BigDecimal getAmount() {
        return amount;
    }

    public Boolean getUserConfirmed() {
        return userConfirmed;
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

    public void updateReview(String status, String approvalId, String handlingNote, LocalDateTime updatedAt) {
        this.status = status;
        this.approvalId = approvalId;
        this.handlingNote = handlingNote;
        this.updatedAt = updatedAt;
    }
}
