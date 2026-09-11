package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class AdminAfterSaleReviewResponse {

    private final String requestNo;
    private final String status;
    private final String approvalNo;
    private final String balanceTransactionNo;
    private final BigDecimal amount;
    private final String reviewerUsername;
    private final LocalDateTime reviewedAt;

    public AdminAfterSaleReviewResponse(String requestNo, String status, String approvalNo,
                                        String balanceTransactionNo, BigDecimal amount,
                                        String reviewerUsername, LocalDateTime reviewedAt) {
        this.requestNo = requestNo;
        this.status = status;
        this.approvalNo = approvalNo;
        this.balanceTransactionNo = balanceTransactionNo;
        this.amount = amount;
        this.reviewerUsername = reviewerUsername;
        this.reviewedAt = reviewedAt;
    }

    public String getRequestNo() { return requestNo; }
    public String getStatus() { return status; }
    public String getApprovalNo() { return approvalNo; }
    public String getBalanceTransactionNo() { return balanceTransactionNo; }
    public BigDecimal getAmount() { return amount; }
    public String getReviewerUsername() { return reviewerUsername; }
    public LocalDateTime getReviewedAt() { return reviewedAt; }
}
