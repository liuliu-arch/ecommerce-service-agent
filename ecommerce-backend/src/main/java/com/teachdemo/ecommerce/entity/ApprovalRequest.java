package com.teachdemo.ecommerce.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import com.teachdemo.ecommerce.service.BusinessException;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class ApprovalRequest {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String approvalId;

    private String businessType;

    private String businessId;

    private String riskLevel;

    private BigDecimal amount;

    private String status;

    private String operator;

    private String comment;

    private LocalDateTime createdAt;

    private LocalDateTime approvedAt;

    protected ApprovalRequest() {
    }

    public ApprovalRequest(String approvalId, String businessType, String businessId, String riskLevel,
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

    public void approve(String operator, String comment, LocalDateTime approvedAt) {
        requirePending();
        this.status = "approved";
        this.operator = operator;
        this.comment = comment;
        this.approvedAt = approvedAt;
    }

    public void reject(String operator, String comment, LocalDateTime approvedAt) {
        requirePending();
        this.status = "rejected";
        this.operator = operator;
        this.comment = comment;
        this.approvedAt = approvedAt;
    }

    private void requirePending() {
        if (!"pending".equals(status)) {
            throw BusinessException.conflict("APPROVAL_ALREADY_DECIDED", "审批已处理，不能重复修改结果");
        }
    }

    public Long getId() {
        return id;
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
