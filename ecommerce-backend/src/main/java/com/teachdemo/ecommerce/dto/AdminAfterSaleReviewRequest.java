package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class AdminAfterSaleReviewRequest {

    private String reviewNote;
    private BigDecimal approvedAmount;

    public String getReviewNote() {
        return reviewNote;
    }

    public BigDecimal getApprovedAmount() {
        return approvedAmount;
    }
}
