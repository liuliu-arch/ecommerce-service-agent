package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class UserPreferenceResponse {

    private final String userId;
    private final String preferredCategories;
    private final String preferredDelivery;
    private final BigDecimal budgetMin;
    private final BigDecimal budgetMax;
    private final Boolean invoiceRequired;

    public UserPreferenceResponse(String userId, String preferredCategories, String preferredDelivery,
                                  BigDecimal budgetMin, BigDecimal budgetMax, Boolean invoiceRequired) {
        this.userId = userId;
        this.preferredCategories = preferredCategories;
        this.preferredDelivery = preferredDelivery;
        this.budgetMin = budgetMin;
        this.budgetMax = budgetMax;
        this.invoiceRequired = invoiceRequired;
    }

    public String getUserId() {
        return userId;
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
