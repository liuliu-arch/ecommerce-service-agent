package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public record ShopOrderResponse(
    String orderNo,
    String orderStatus,
    String paymentStatus,
    String fulfillmentStatus,
    BigDecimal totalAmount,
    String itemSummary,
    String remark,
    String logisticsNo,
    List<ShopOrderItemResponse> items,
    Boolean afterSaleAvailable,
    List<String> availableAfterSaleTypes,
    LocalDateTime createdAt,
    LocalDateTime paidAt,
    LocalDateTime shippedAt,
    LocalDateTime signedAt,
    LocalDateTime completedAt
) {
}
