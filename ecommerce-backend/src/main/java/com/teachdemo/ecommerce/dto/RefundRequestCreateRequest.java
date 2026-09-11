package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class RefundRequestCreateRequest {

    private String orderNo;
    private String userId;
    private BigDecimal amount;
    private String reason;

    public String getOrderNo() {
        return orderNo;
    }

    public String getUserId() {
        return userId;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public String getReason() {
        return reason;
    }
}
