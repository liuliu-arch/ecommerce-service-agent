package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Schema(description = "User coupon benefit")
public class UserCouponResponse {

    @Schema(description = "Coupon code", example = "CP-U1001-AUD-70")
    private final String couponCode;
    @Schema(description = "Coupon name", example = "金卡会员耳机专享券")
    private final String couponName;
    @Schema(description = "Coupon type", example = "amount_off")
    private final String couponType;
    @Schema(description = "Discount amount", example = "70.00")
    private final BigDecimal discountAmount;
    @Schema(description = "Minimum order amount", example = "500.00")
    private final BigDecimal thresholdAmount;
    @Schema(description = "Comma-separated applicable product categories", example = "消费电子,耳机")
    private final String applicableCategories;
    @Schema(description = "Coupon start time")
    private final LocalDateTime startAt;
    @Schema(description = "Coupon end time")
    private final LocalDateTime endAt;
    @Schema(description = "Coupon status", example = "available")
    private final String status;

    public UserCouponResponse(String couponCode, String couponName, String couponType,
                              BigDecimal discountAmount, BigDecimal thresholdAmount,
                              String applicableCategories, LocalDateTime startAt,
                              LocalDateTime endAt, String status) {
        this.couponCode = couponCode;
        this.couponName = couponName;
        this.couponType = couponType;
        this.discountAmount = discountAmount;
        this.thresholdAmount = thresholdAmount;
        this.applicableCategories = applicableCategories;
        this.startAt = startAt;
        this.endAt = endAt;
        this.status = status;
    }

    public String getCouponCode() {
        return couponCode;
    }

    public String getCouponName() {
        return couponName;
    }

    public String getCouponType() {
        return couponType;
    }

    public BigDecimal getDiscountAmount() {
        return discountAmount;
    }

    public BigDecimal getThresholdAmount() {
        return thresholdAmount;
    }

    public String getApplicableCategories() {
        return applicableCategories;
    }

    public LocalDateTime getStartAt() {
        return startAt;
    }

    public LocalDateTime getEndAt() {
        return endAt;
    }

    public String getStatus() {
        return status;
    }
}
