package com.teachdemo.ecommerce.dto;

import java.time.LocalDateTime;
import java.util.List;

public class AdminPromotionResponse {

    private final String promotionName;
    private final String promotionType;
    private final String discountSummary;
    private final String requiredMemberLevel;
    private final String conditionSummary;
    private final LocalDateTime startAt;
    private final LocalDateTime endAt;
    private final Boolean active;
    private final Integer productCount;
    private final List<AdminPromotionProductResponse> products;

    public AdminPromotionResponse(String promotionName, String promotionType, String discountSummary,
                                  String requiredMemberLevel, String conditionSummary,
                                  LocalDateTime startAt, LocalDateTime endAt, Boolean active,
                                  Integer productCount, List<AdminPromotionProductResponse> products) {
        this.promotionName = promotionName;
        this.promotionType = promotionType;
        this.discountSummary = discountSummary;
        this.requiredMemberLevel = requiredMemberLevel;
        this.conditionSummary = conditionSummary;
        this.startAt = startAt;
        this.endAt = endAt;
        this.active = active;
        this.productCount = productCount;
        this.products = products;
    }

    public String getPromotionName() {
        return promotionName;
    }

    public String getPromotionType() {
        return promotionType;
    }

    public String getDiscountSummary() {
        return discountSummary;
    }

    public String getRequiredMemberLevel() {
        return requiredMemberLevel;
    }

    public String getConditionSummary() {
        return conditionSummary;
    }

    public LocalDateTime getStartAt() {
        return startAt;
    }

    public LocalDateTime getEndAt() {
        return endAt;
    }

    public Boolean getActive() {
        return active;
    }

    public Integer getProductCount() {
        return productCount;
    }

    public List<AdminPromotionProductResponse> getProducts() {
        return products;
    }
}
