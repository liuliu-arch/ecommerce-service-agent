package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.RefundRequestCreateRequest;
import com.teachdemo.ecommerce.dto.RefundRequestResponse;
import com.teachdemo.ecommerce.entity.RefundRequest;
import com.teachdemo.ecommerce.repository.OrderRepository;
import com.teachdemo.ecommerce.repository.RefundRequestRepository;
import java.time.LocalDateTime;
import java.util.Objects;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class RefundRequestService {

    private final RefundRequestRepository refundRequestRepository;
    private final OrderRepository orderRepository;

    public RefundRequestService(RefundRequestRepository refundRequestRepository, OrderRepository orderRepository) {
        this.refundRequestRepository = refundRequestRepository;
        this.orderRepository = orderRepository;
    }

    public RefundRequestResponse getByRequestId(String requestId, String currentUserId) {
        RefundRequest request = refundRequestRepository.findByRequestId(requestId)
            .orElseThrow(() -> new IllegalArgumentException("Refund request not found: " + requestId));
        assertOrderOwner(request.getUserId(), currentUserId);
        return toResponse(request);
    }

    @Transactional
    public RefundRequestResponse create(RefundRequestCreateRequest request, String currentUserId) {
        var order = orderRepository.findByOrderNo(request.getOrderNo())
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + request.getOrderNo()));
        assertOrderOwner(order.getUserId(), currentUserId);
        LocalDateTime now = LocalDateTime.now();
        String requestId = "RF-" + (1000 + refundRequestRepository.count() + 1);
        RefundRequest entity = new RefundRequest(requestId, request.getOrderNo(), currentUserId,
            request.getAmount(), request.getReason(), "pending_approval", null, now, now);
        RefundRequest saved = refundRequestRepository.save(entity);
        order.markAfterSaleRequested();
        orderRepository.save(order);
        return toResponse(saved);
    }

    private void assertOrderOwner(String orderUserId, String currentUserId) {
        // 当前用户来自登录主体或已认证 Agent 服务，不能使用请求体里的 userId 做授权。
        if (!StringUtils.hasText(currentUserId) || !Objects.equals(orderUserId, currentUserId)) {
            throw BusinessException.forbidden("ORDER_ACCESS_DENIED", "只能访问或处理当前用户自己的订单");
        }
    }

    private RefundRequestResponse toResponse(RefundRequest request) {
        return new RefundRequestResponse(request.getRequestId(), request.getOrderNo(), request.getUserId(),
            request.getAmount(), request.getReason(), request.getStatus(), request.getApprovalId(),
            request.getCreatedAt(), request.getUpdatedAt());
    }
}
