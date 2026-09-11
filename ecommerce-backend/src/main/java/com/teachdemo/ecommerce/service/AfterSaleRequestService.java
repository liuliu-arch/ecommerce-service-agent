package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.AfterSaleRequestCreateRequest;
import com.teachdemo.ecommerce.dto.AfterSaleRequestResponse;
import com.teachdemo.ecommerce.entity.AfterSaleRequest;
import com.teachdemo.ecommerce.repository.AfterSaleRequestRepository;
import com.teachdemo.ecommerce.repository.OrderRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class AfterSaleRequestService {

    private final AfterSaleRequestRepository afterSaleRequestRepository;
    private final OrderRepository orderRepository;

    public AfterSaleRequestService(AfterSaleRequestRepository afterSaleRequestRepository,
                                   OrderRepository orderRepository) {
        this.afterSaleRequestRepository = afterSaleRequestRepository;
        this.orderRepository = orderRepository;
    }

    public AfterSaleRequestResponse getByRequestId(String requestId, String currentUserId) {
        AfterSaleRequest request = afterSaleRequestRepository.findByRequestId(requestId)
            .orElseThrow(() -> new IllegalArgumentException("After-sale request not found: " + requestId));
        assertOrderOwner(request.getUserId(), currentUserId);
        return toResponse(request);
    }

    public List<AfterSaleRequestResponse> listByOrderNo(String orderNo, String currentUserId) {
        var order = orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderNo));
        assertOrderOwner(order.getUserId(), currentUserId);
        return afterSaleRequestRepository.findByOrderNo(orderNo).stream()
            .map(this::toResponse)
            .collect(Collectors.toList());
    }

    @Transactional
    public AfterSaleRequestResponse create(AfterSaleRequestCreateRequest request, String currentUserId) {
        var order = orderRepository.findByOrderNo(request.getOrderNo())
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + request.getOrderNo()));
        assertOrderOwner(order.getUserId(), currentUserId);
        LocalDateTime now = LocalDateTime.now();
        String requestId = "AS-" + (1000 + afterSaleRequestRepository.count() + 1);
        AfterSaleRequest entity = new AfterSaleRequest(requestId, request.getOrderNo(), currentUserId,
            request.getRequestType(), request.getReason(), "draft", null, now, now, "售后申请草稿已创建，等待后续确认。");
        AfterSaleRequest saved = afterSaleRequestRepository.save(entity);
        order.markAfterSaleRequested();
        orderRepository.save(order);
        return toResponse(saved);
    }

    private void assertOrderOwner(String orderUserId, String currentUserId) {
        // 售后草稿会占用订单资格，身份必须来自登录主体或已认证 Agent 服务。
        if (!StringUtils.hasText(currentUserId) || !Objects.equals(orderUserId, currentUserId)) {
            throw BusinessException.forbidden("ORDER_ACCESS_DENIED", "只能访问或处理当前用户自己的订单");
        }
    }

    private AfterSaleRequestResponse toResponse(AfterSaleRequest request) {
        return new AfterSaleRequestResponse(request.getRequestId(), request.getOrderNo(), request.getUserId(),
            request.getRequestType(), request.getReason(), request.getStatus(), request.getApprovalId(),
            request.getCreatedAt(), request.getUpdatedAt(), request.getHandlingNote());
    }
}
