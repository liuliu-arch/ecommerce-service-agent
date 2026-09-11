package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public class AdminAfterSaleResponse {

    private final String requestNo;
    private final String orderNo;
    private final String userId;
    private final String userNickname;
    private final String type;
    private final String status;
    private final BigDecimal amount;
    private final String reason;
    private final String handlingNote;
    private final List<ApprovalRecordResponse> approvalRecords;
    private final BigDecimal balanceEffectPreview;
    private final LocalDateTime createdAt;
    private final LocalDateTime updatedAt;

    public AdminAfterSaleResponse(String requestNo, String orderNo, String userId, String userNickname,
                                  String type, String status, BigDecimal amount, String reason,
                                  String handlingNote, List<ApprovalRecordResponse> approvalRecords,
                                  BigDecimal balanceEffectPreview, LocalDateTime createdAt,
                                  LocalDateTime updatedAt) {
        this.requestNo = requestNo;
        this.orderNo = orderNo;
        this.userId = userId;
        this.userNickname = userNickname;
        this.type = type;
        this.status = status;
        this.amount = amount;
        this.reason = reason;
        this.handlingNote = handlingNote;
        this.approvalRecords = approvalRecords;
        this.balanceEffectPreview = balanceEffectPreview;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public String getRequestNo() { return requestNo; }
    public String getOrderNo() { return orderNo; }
    public String getUserId() { return userId; }
    public String getUserNickname() { return userNickname; }
    public String getType() { return type; }
    public String getStatus() { return status; }
    public BigDecimal getAmount() { return amount; }
    public String getReason() { return reason; }
    public String getHandlingNote() { return handlingNote; }
    public List<ApprovalRecordResponse> getApprovalRecords() { return approvalRecords; }
    public BigDecimal getBalanceEffectPreview() { return balanceEffectPreview; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}
