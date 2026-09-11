package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.ApprovalRequest;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ApprovalRequestRepository extends JpaRepository<ApprovalRequest, Long> {

    Optional<ApprovalRequest> findByApprovalId(String approvalId);
}
