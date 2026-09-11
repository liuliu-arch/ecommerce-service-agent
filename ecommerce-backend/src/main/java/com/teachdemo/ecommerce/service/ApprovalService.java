package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.ApprovalCreateRequest;
import com.teachdemo.ecommerce.dto.ApprovalDecisionRequest;
import com.teachdemo.ecommerce.dto.ApprovalResponse;
import com.teachdemo.ecommerce.entity.ApprovalRequest;
import com.teachdemo.ecommerce.repository.ApprovalRequestRepository;
import java.time.LocalDateTime;
import org.springframework.stereotype.Service;

@Service
public class ApprovalService {

    private final ApprovalRequestRepository approvalRequestRepository;

    public ApprovalService(ApprovalRequestRepository approvalRequestRepository) {
        this.approvalRequestRepository = approvalRequestRepository;
    }

    public ApprovalResponse getByApprovalId(String approvalId) {
        ApprovalRequest request = findApproval(approvalId);
        return toResponse(request);
    }

    public ApprovalResponse create(ApprovalCreateRequest request) {
        String approvalId = "AP-" + (1000 + approvalRequestRepository.count() + 1);
        ApprovalRequest entity = new ApprovalRequest(approvalId, request.getBusinessType(), request.getBusinessId(),
            request.getRiskLevel(), request.getAmount(), "pending", null, request.getReason(), LocalDateTime.now(), null);
        return toResponse(approvalRequestRepository.save(entity));
    }

    public ApprovalResponse approve(String approvalId, ApprovalDecisionRequest decision) {
        ApprovalRequest request = findApproval(approvalId);
        request.approve(decision.getOperator(), decision.getComment(), LocalDateTime.now());
        return toResponse(approvalRequestRepository.save(request));
    }

    public ApprovalResponse reject(String approvalId, ApprovalDecisionRequest decision) {
        ApprovalRequest request = findApproval(approvalId);
        request.reject(decision.getOperator(), decision.getComment(), LocalDateTime.now());
        return toResponse(approvalRequestRepository.save(request));
    }

    private ApprovalRequest findApproval(String approvalId) {
        return approvalRequestRepository.findByApprovalId(approvalId)
            .orElseThrow(() -> new IllegalArgumentException("Approval not found: " + approvalId));
    }

    private ApprovalResponse toResponse(ApprovalRequest request) {
        return new ApprovalResponse(request.getApprovalId(), request.getBusinessType(), request.getBusinessId(),
            request.getRiskLevel(), request.getAmount(), request.getStatus(), request.getOperator(),
            request.getComment(), request.getCreatedAt(), request.getApprovedAt());
    }
}
