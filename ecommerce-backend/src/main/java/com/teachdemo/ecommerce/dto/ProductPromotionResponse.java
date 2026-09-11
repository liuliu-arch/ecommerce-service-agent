package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Schema(description = "Current product promotion facts")
public class ProductPromotionResponse {

    @Schema(description = "Promotion ID", example = "1")
    private final Long id;
    @Schema(description = "Promotion name", example = "通勤数码会员日")
    private final String promotionName;
    @Schema(description = "Promotion type", example = "member_discount")
    private final String promotionType;
    @Schema(description = "Discount summary", example = "会员到手价 529 元，较日常价优惠 70 元")
    private final String discountSummary;
    @Schema(description = "Promotional price", example = "529.00")
    private final BigDecimal promotionPrice;
    @Schema(description = "Required member level, if this promotion is conditional", example = "gold")
    private final String requiredMemberLevel;
    @Schema(description = "Human-readable promotion condition", example = "金卡会员专享")
    private final String conditionSummary;
    @Schema(description = "Promotion start time")
    private final LocalDateTime startAt;
    @Schema(description = "Promotion end time")
    private final LocalDateTime endAt;

    public ProductPromotionResponse(Long id, String promotionName, String promotionType, String discountSummary,
                                    BigDecimal promotionPrice, LocalDateTime startAt, LocalDateTime endAt) {
        this(id, promotionName, promotionType, discountSummary, promotionPrice, null, "", startAt, endAt);
    }

    public ProductPromotionResponse(Long id, String promotionName, String promotionType, String discountSummary,
                                    BigDecimal promotionPrice, String requiredMemberLevel, String conditionSummary,
                                    LocalDateTime startAt, LocalDateTime endAt) {
        this.id = id;
        this.promotionName = promotionName;
        this.promotionType = promotionType;
        this.discountSummary = discountSummary;
        this.promotionPrice = promotionPrice;
        this.requiredMemberLevel = requiredMemberLevel;
        this.conditionSummary = conditionSummary;
        this.startAt = startAt;
        this.endAt = endAt;
    }

    public Long getId() {
        return id;
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
}
