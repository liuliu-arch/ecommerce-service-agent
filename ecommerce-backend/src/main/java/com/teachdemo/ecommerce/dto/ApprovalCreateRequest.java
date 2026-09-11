package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class ApprovalCreateRequest {

    private String businessType;
    private String businessId;
    private String riskLevel;
    private BigDecimal amount;
    private String reason;

    public String getBusinessType() {
        return businessType;
    }

    public String getBusinessId() {
        return businessId;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public String getReason() {
        return reason;
    }
}
