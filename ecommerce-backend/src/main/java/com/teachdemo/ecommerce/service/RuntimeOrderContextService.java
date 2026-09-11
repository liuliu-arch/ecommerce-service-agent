package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.RuntimeOrderItemSummaryResponse;
import com.teachdemo.ecommerce.dto.RuntimeOrderContextResponse;
import com.teachdemo.ecommerce.dto.RuntimeOrderSummaryResponse;
import com.teachdemo.ecommerce.entity.OrderEntity;
import com.teachdemo.ecommerce.entity.OrderItem;
import com.teachdemo.ecommerce.repository.OrderItemRepository;
import com.teachdemo.ecommerce.repository.OrderRepository;
import com.teachdemo.ecommerce.repository.ProductRepository;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class RuntimeOrderContextService {

    private final UserProfileRepository userProfileRepository;
    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final ProductRepository productRepository;
    private final int defaultLimit;
    private final int maxLimit;

    public RuntimeOrderContextService(UserProfileRepository userProfileRepository,
                                      OrderRepository orderRepository,
                                      OrderItemRepository orderItemRepository,
                                      ProductRepository productRepository,
                                      @Value("${customer-service.runtime-context.default-order-limit:10}") int defaultLimit,
                                      @Value("${customer-service.runtime-context.max-order-limit:50}") int maxLimit) {
        this.userProfileRepository = userProfileRepository;
        this.orderRepository = orderRepository;
        this.orderItemRepository = orderItemRepository;
        this.productRepository = productRepository;
        this.maxLimit = Math.max(1, maxLimit);
        this.defaultLimit = Math.max(1, Math.min(defaultLimit, this.maxLimit));
    }

    public RuntimeOrderContextResponse loadCurrentUserOrders(String userId, Integer month, Integer limit) {
        userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> BusinessException.notFound("USER_NOT_FOUND", "用户不存在"));
        if (month != null && (month < 1 || month > 12)) {
            throw BusinessException.badRequest("ORDER_MONTH_INVALID", "订单月份必须在 1 到 12 之间");
        }
        int boundedLimit = limit == null ? defaultLimit : Math.max(1, Math.min(limit, maxLimit));
        List<OrderEntity> matchedOrders = orderRepository.findByUserIdOrderByCreatedAtDesc(userId).stream()
            .filter(order -> month == null
                || order.getCreatedAt() != null && order.getCreatedAt().getMonthValue() == month)
            .toList();
        List<RuntimeOrderSummaryResponse> orders = matchedOrders.stream()
            .limit(boundedLimit)
            .map(order -> {
                List<OrderItem> orderItems = orderItemRepository.findByOrderEntity(order);
                List<RuntimeOrderItemSummaryResponse> items = orderItems.stream()
                    .map(this::toRuntimeItem)
                    .toList();
                return new RuntimeOrderSummaryResponse(
                    order.getOrderNo(),
                    order.getStatus(),
                    order.getPaymentStatus(),
                    order.getFulfillmentStatus(),
                    order.getTotalAmount(),
                    order.getCreatedAt(),
                    order.getPaidAt(),
                    order.getShippedAt(),
                    order.getDeliveredAt(),
                    order.getLogisticsNo(),
                    orderItems.stream().map(OrderItem::getProductName).toList(),
                    items,
                    aggregateReturnable(items)
                );
            })
            .toList();
        return new RuntimeOrderContextResponse(orders, matchedOrders.size() > boundedLimit, boundedLimit);
    }

    private RuntimeOrderItemSummaryResponse toRuntimeItem(OrderItem item) {
        Boolean returnable = item.getProductId() == null
            ? null
            : productRepository.findById(item.getProductId())
                .map(product -> product.getReturnable())
                .orElse(null);
        return new RuntimeOrderItemSummaryResponse(item.getProductName(), item.getQuantity(), returnable);
    }

    private Boolean aggregateReturnable(List<RuntimeOrderItemSummaryResponse> items) {
        if (items.isEmpty() || items.stream().anyMatch(item -> item.returnable() == null)) {
            return null;
        }
        return items.stream().allMatch(item -> Boolean.TRUE.equals(item.returnable()));
    }
}
