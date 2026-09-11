package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record ShopAfterSaleResponse(
    String requestNo,
    String orderNo,
    String type,
    String status,
    BigDecimal amount,
    String reason,
    LocalDateTime createdAt
) {
}
