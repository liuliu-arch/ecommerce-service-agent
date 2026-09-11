package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class AdminPromotionProductRequest {

    private Long productId;
    private BigDecimal promotionPrice;

    public Long getProductId() {
        return productId;
    }

    public BigDecimal getPromotionPrice() {
        return promotionPrice;
    }
}
