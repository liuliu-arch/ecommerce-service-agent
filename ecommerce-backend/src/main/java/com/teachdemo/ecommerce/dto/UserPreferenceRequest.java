package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class UserPreferenceRequest {

    private String preferredCategories;
    private String preferredDelivery;
    private BigDecimal budgetMin;
    private BigDecimal budgetMax;
    private Boolean invoiceRequired;

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
