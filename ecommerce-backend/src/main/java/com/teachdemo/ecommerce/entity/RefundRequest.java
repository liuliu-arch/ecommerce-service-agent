package com.teachdemo.ecommerce.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class RefundRequest {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String requestId;

    private String orderNo;

    private String userId;

    private BigDecimal amount;

    private String reason;

    private String status;

    private String approvalId;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    protected RefundRequest() {
    }

    public RefundRequest(String requestId, String orderNo, String userId, BigDecimal amount,
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
