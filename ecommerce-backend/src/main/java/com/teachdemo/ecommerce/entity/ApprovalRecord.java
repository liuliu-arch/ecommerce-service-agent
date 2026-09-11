package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "approval_record")
public class ApprovalRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String approvalNo;

    private String targetType;

    private String targetNo;

    private String status;

    private String reviewerUsername;

    private String reviewNote;

    private LocalDateTime createdAt;

    private LocalDateTime reviewedAt;

    protected ApprovalRecord() {
    }

    public ApprovalRecord(String approvalNo, String targetType, String targetNo, String status,
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

    public Long getId() {
        return id;
    }

    public String getApprovalNo() {
        return approvalNo;
    }

    public String getTargetType() {
        return targetType;
    }

    public String getTargetNo() {
        return targetNo;
    }

    public String getStatus() {
        return status;
    }

    public String getReviewerUsername() {
        return reviewerUsername;
    }

    public String getReviewNote() {
        return reviewNote;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getReviewedAt() {
        return reviewedAt;
    }
}
