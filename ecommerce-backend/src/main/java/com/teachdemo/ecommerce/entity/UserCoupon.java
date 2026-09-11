package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
public class UserCoupon {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String userId;

    @Column(nullable = false, unique = true)
    private String couponCode;

    private String couponName;

    private String couponType;

    private BigDecimal discountAmount;

    private BigDecimal thresholdAmount;

    private String applicableCategories;

    private LocalDateTime startAt;

    private LocalDateTime endAt;

    private String status;

    protected UserCoupon() {
    }

    public UserCoupon(String userId, String couponCode, String couponName, String couponType,
                      BigDecimal discountAmount, BigDecimal thresholdAmount, String applicableCategories,
                      LocalDateTime startAt, LocalDateTime endAt, String status) {
        this.userId = userId;
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

    public Long getId() {
        return id;
    }

    public String getUserId() {
        return userId;
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
