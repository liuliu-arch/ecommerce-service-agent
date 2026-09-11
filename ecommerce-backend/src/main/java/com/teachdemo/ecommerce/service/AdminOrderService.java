package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.AdminOrderResponse;
import com.teachdemo.ecommerce.dto.AdminOrderUpdateRequest;
import com.teachdemo.ecommerce.dto.AfterSaleRequestResponse;
import com.teachdemo.ecommerce.dto.LogisticsEventResponse;
import com.teachdemo.ecommerce.dto.OrderItemResponse;
import com.teachdemo.ecommerce.entity.AfterSaleRequest;
import com.teachdemo.ecommerce.entity.LogisticsInfo;
import com.teachdemo.ecommerce.entity.OrderEntity;
import com.teachdemo.ecommerce.entity.UserProfile;
import com.teachdemo.ecommerce.repository.AfterSaleRequestRepository;
import com.teachdemo.ecommerce.repository.LogisticsEventRepository;
import com.teachdemo.ecommerce.repository.LogisticsInfoRepository;
import com.teachdemo.ecommerce.repository.OrderItemRepository;
import com.teachdemo.ecommerce.repository.OrderRepository;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class AdminOrderService {

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final LogisticsInfoRepository logisticsInfoRepository;
    private final LogisticsEventRepository logisticsEventRepository;
    private final AfterSaleRequestRepository afterSaleRequestRepository;
    private final UserProfileRepository userProfileRepository;

    public AdminOrderService(OrderRepository orderRepository, OrderItemRepository orderItemRepository,
                             LogisticsInfoRepository logisticsInfoRepository,
                             LogisticsEventRepository logisticsEventRepository,
                             AfterSaleRequestRepository afterSaleRequestRepository,
                             UserProfileRepository userProfileRepository) {
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.logisticsInfoRepository = logisticsInfoRepository;
        this.logisticsEventRepository = logisticsEventRepository;
        this.afterSaleRequestRepository = afterSaleRequestRepository;
        this.userProfileRepository = userProfileRepository;
    }

    public List<AdminOrderResponse> list(String orderNo, String userId, String orderStatus,
                                         String paymentStatus, String fulfillmentStatus) {
        return orderRepository.findAll().stream()
            .filter(order -> !StringUtils.hasText(orderNo) || order.getOrderNo().contains(orderNo))
            .filter(order -> !StringUtils.hasText(userId) || userId.equals(order.getUserId()))
            .filter(order -> !StringUtils.hasText(orderStatus) || orderStatus.equalsIgnoreCase(order.getStatus()))
            .filter(order -> !StringUtils.hasText(paymentStatus) || paymentStatus.equalsIgnoreCase(order.getPaymentStatus()))
            .filter(order -> !StringUtils.hasText(fulfillmentStatus) || fulfillmentStatus.equalsIgnoreCase(order.getFulfillmentStatus()))
            .sorted(Comparator.comparing(OrderEntity::getCreatedAt, Comparator.nullsLast(Comparator.naturalOrder())).reversed())
            .map(this::toResponse)
            .toList();
    }

    public AdminOrderResponse get(String orderNo) {
        return toResponse(findOrder(orderNo));
    }

    @Transactional
    public AdminOrderResponse update(String orderNo, AdminOrderUpdateRequest request) {
        OrderEntity order = findOrder(orderNo);
        validateStatus(request.getOrderStatus(), "ORDER_STATUS_INVALID", "订单状态不合法");
        validateStatus(request.getFulfillmentStatus(), "ORDER_STATUS_INVALID", "发货状态不合法");
        // 后台订单修改只维护运营字段，资金结果必须留给售后审批流程处理。
        order.updateAdminFields(request.getOrderStatus(), request.getFulfillmentStatus(),
            request.getLogisticsNo(), request.getRemark(), LocalDateTime.now());
        return toResponse(order);
    }

    private OrderEntity findOrder(String orderNo) {
        return orderRepository.findByOrderNo(orderNo)
            .orElseThrow(() -> BusinessException.notFound("ORDER_NOT_FOUND", "订单不存在"));
    }

    private void validateStatus(String status, String code, String message) {
        if (status != null && status.isBlank()) {
            throw BusinessException.badRequest(code, message);
        }
    }

    private AdminOrderResponse toResponse(OrderEntity order) {
        UserProfile user = order.getUserId() == null ? null :
            userProfileRepository.findByUserId(order.getUserId()).orElse(null);
        List<OrderItemResponse> items = orderItemRepository.findByOrderEntity(order).stream()
            .map(item -> new OrderItemResponse(item.getProductId(), item.getProductName(), item.getQuantity(), item.getUnitPrice()))
            .toList();
        List<LogisticsEventResponse> events = logisticsInfoRepository.findByOrderEntity(order)
            .map(this::toLogisticsEvents)
            .orElse(List.of());
        List<AfterSaleRequestResponse> afterSales = afterSaleRequestRepository.findByOrderNo(order.getOrderNo()).stream()
            .map(this::toAfterSaleResponse)
            .toList();
        String logisticsNo = order.getLogisticsNo();
        if (!StringUtils.hasText(logisticsNo)) {
            logisticsNo = logisticsInfoRepository.findByOrderEntity(order).map(LogisticsInfo::getTrackingNo).orElse(null);
        }
        return new AdminOrderResponse(order.getOrderNo(), order.getUserId(),
            user == null ? null : user.getNickname(), user == null ? null : user.getMobile(),
            order.getStatus(), order.getPaymentStatus(), order.getFulfillmentStatus(), order.getTotalAmount(),
            logisticsNo, order.getRemark(), order.getCreatedAt(), order.getPaidAt(), order.getShippedAt(),
            order.getDeliveredAt(), items, events, afterSales);
    }

    private List<LogisticsEventResponse> toLogisticsEvents(LogisticsInfo info) {
        return logisticsEventRepository.findByLogisticsInfoOrderByOccurredAtDesc(info).stream()
            .map(event -> new LogisticsEventResponse(event.getOccurredAt(), event.getContent()))
            .toList();
    }

    private AfterSaleRequestResponse toAfterSaleResponse(AfterSaleRequest request) {
        return new AfterSaleRequestResponse(request.getRequestId(), request.getOrderNo(), request.getUserId(),
            request.getRequestType(), request.getReason(), request.getStatus(), request.getApprovalId(),
            request.getCreatedAt(), request.getUpdatedAt(), request.getHandlingNote());
    }
}
