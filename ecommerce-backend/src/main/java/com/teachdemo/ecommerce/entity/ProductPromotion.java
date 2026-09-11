package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
public class ProductPromotion {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long productId;

    @Column(nullable = false)
    private String promotionName;

    private String promotionType;

    private String discountSummary;

    private BigDecimal promotionPrice;

    private String requiredMemberLevel;

    private String conditionSummary;

    private LocalDateTime startAt;

    private LocalDateTime endAt;

    private Boolean active;

    protected ProductPromotion() {
    }

    public ProductPromotion(Long productId, String promotionName, String promotionType, String discountSummary,
                            BigDecimal promotionPrice, LocalDateTime startAt, LocalDateTime endAt, Boolean active) {
        this(productId, promotionName, promotionType, discountSummary, promotionPrice, null, "", startAt, endAt, active);
    }

    public ProductPromotion(Long productId, String promotionName, String promotionType, String discountSummary,
                            BigDecimal promotionPrice, String requiredMemberLevel, String conditionSummary,
                            LocalDateTime startAt, LocalDateTime endAt, Boolean active) {
        this.productId = productId;
        this.promotionName = promotionName;
        this.promotionType = promotionType;
        this.discountSummary = discountSummary;
        this.promotionPrice = promotionPrice;
        this.requiredMemberLevel = requiredMemberLevel;
        this.conditionSummary = conditionSummary;
        this.startAt = startAt;
        this.endAt = endAt;
        this.active = active;
    }

    public void updatePromotionFacts(String promotionName, String promotionType, String discountSummary, BigDecimal promotionPrice,
                                     String requiredMemberLevel, String conditionSummary,
                                     LocalDateTime startAt, LocalDateTime endAt, Boolean active) {
        this.promotionName = promotionName;
        this.promotionType = promotionType;
        this.discountSummary = discountSummary;
        this.promotionPrice = promotionPrice;
        this.requiredMemberLevel = requiredMemberLevel;
        this.conditionSummary = conditionSummary;
        this.startAt = startAt;
        this.endAt = endAt;
        this.active = active;
    }

    public Long getId() {
        return id;
    }

    public Long getProductId() {
        return productId;
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

    public BigDecimal getPromotionPrice() {
        return promotionPrice;
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
}
