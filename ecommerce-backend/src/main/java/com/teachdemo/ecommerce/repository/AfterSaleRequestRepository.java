package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.AfterSaleRequest;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AfterSaleRequestRepository extends JpaRepository<AfterSaleRequest, Long> {

    Optional<AfterSaleRequest> findByRequestId(String requestId);

    List<AfterSaleRequest> findByOrderNo(String orderNo);

    Optional<AfterSaleRequest> findByRequestIdAndUserId(String requestId, String userId);

    List<AfterSaleRequest> findByUserId(String userId);

    boolean existsByOrderNoAndUserIdAndRequestTypeAndStatus(String orderNo, String userId,
                                                            String requestType, String status);
}
