package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public record ShopProductResponse(
    Long productId,
    String name,
    String category,
    String description,
    BigDecimal price,
    Integer stockQuantity,
    String imageUrl,
    Boolean supportsSevenDayReturn,
    String afterSaleNote,
    Boolean purchaseAvailable,
    ProductPromotionResponse promotion
) {
}
