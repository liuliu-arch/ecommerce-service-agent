package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class AdminPromotionProductResponse {

    private final Long productId;
    private final String productCode;
    private final String productName;
    private final String category;
    private final BigDecimal originalPrice;
    private final BigDecimal promotionPrice;
    private final Boolean participating;

    public AdminPromotionProductResponse(Long productId, String productCode, String productName, String category,
                                         BigDecimal originalPrice, BigDecimal promotionPrice, Boolean participating) {
        this.productId = productId;
        this.productCode = productCode;
        this.productName = productName;
        this.category = category;
        this.originalPrice = originalPrice;
        this.promotionPrice = promotionPrice;
        this.participating = participating;
    }

    public Long getProductId() {
        return productId;
    }

    public String getProductCode() {
        return productCode;
    }

    public String getProductName() {
        return productName;
    }

    public String getCategory() {
        return category;
    }

    public BigDecimal getOriginalPrice() {
        return originalPrice;
    }

    public BigDecimal getPromotionPrice() {
        return promotionPrice;
    }

    public Boolean getParticipating() {
        return participating;
    }
}
