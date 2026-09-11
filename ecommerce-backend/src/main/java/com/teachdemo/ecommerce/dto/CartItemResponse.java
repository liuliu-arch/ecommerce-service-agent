package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public record CartItemResponse(
    Long itemId,
    Long productId,
    String productName,
    String productImageUrl,
    BigDecimal originalUnitPrice,
    BigDecimal unitPrice,
    BigDecimal promotionPrice,
    String promotionName,
    Boolean promotionApplied,
    String promotionCondition,
    Integer quantity,
    Boolean selected,
    Integer stockQuantity,
    String productStatus,
    Boolean settlementAvailable,
    String unavailableReason
) {
}
