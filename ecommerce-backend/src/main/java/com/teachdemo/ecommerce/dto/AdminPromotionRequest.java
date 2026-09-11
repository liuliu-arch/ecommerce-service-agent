package com.teachdemo.ecommerce.dto;

import java.time.LocalDateTime;
import java.util.List;

public class AdminPromotionRequest {

    private String promotionName;
    private String promotionType;
    private String discountSummary;
    private String requiredMemberLevel;
    private String conditionSummary;
    private LocalDateTime startAt;
    private LocalDateTime endAt;
    private Boolean active;
    private List<AdminPromotionProductRequest> products;

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

    public List<AdminPromotionProductRequest> getProducts() {
        return products;
    }
}
