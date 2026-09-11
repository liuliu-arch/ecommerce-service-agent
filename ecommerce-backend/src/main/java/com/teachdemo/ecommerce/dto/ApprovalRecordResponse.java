package com.teachdemo.ecommerce.dto;

import java.time.LocalDateTime;

public class ApprovalRecordResponse {

    private final String approvalNo;
    private final String targetType;
    private final String targetNo;
    private final String status;
    private final String reviewerUsername;
    private final String reviewNote;
    private final LocalDateTime createdAt;
    private final LocalDateTime reviewedAt;

    public ApprovalRecordResponse(String approvalNo, String targetType, String targetNo, String status,
                                  String reviewerUsername, String reviewNote, LocalDateTime createdAt,
                                  LocalDateTime reviewedAt) {
        this.approvalNo = approvalNo;
        this.targetType = targetType;
        this.targetNo = targetNo;
        this.status = status;
        this.reviewerUsername = reviewerUsername;
        this.reviewNote = reviewNote;
        this.createdAt = createdAt;
        this.reviewedAt = reviewedAt;
    }

    public String getApprovalNo() { return approvalNo; }
    public String getTargetType() { return targetType; }
    public String getTargetNo() { return targetNo; }
    public String getStatus() { return status; }
    public String getReviewerUsername() { return reviewerUsername; }
    public String getReviewNote() { return reviewNote; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getReviewedAt() { return reviewedAt; }
}
