package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public record ShopOrderItemResponse(
    Long productId,
    String productName,
    String productImageUrl,
    BigDecimal unitPrice,
    Integer quantity
) {
}
