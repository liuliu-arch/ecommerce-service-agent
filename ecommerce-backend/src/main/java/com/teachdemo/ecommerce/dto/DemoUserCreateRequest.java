package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class DemoUserCreateRequest {

    private String userId;
    private String nickname;
    private String memberLevel;
    private String riskLevel;
    private String preferredCategories;
    private String preferredDelivery;
    private BigDecimal budgetMin;
    private BigDecimal budgetMax;
    private Boolean invoiceRequired;

    public String getUserId() {
        return userId;
    }

    public String getNickname() {
        return nickname;
    }

    public String getMemberLevel() {
        return memberLevel;
    }

    public String getRiskLevel() {
        return riskLevel;
    }

    public String getPreferredCategories() {
        return preferredCategories;
    }

    public String getPreferredDelivery() {
        return preferredDelivery;
    }

    public BigDecimal getBudgetMin() {
        return budgetMin;
    }

    public BigDecimal getBudgetMax() {
        return budgetMax;
    }

    public Boolean getInvoiceRequired() {
        return invoiceRequired;
    }
}
