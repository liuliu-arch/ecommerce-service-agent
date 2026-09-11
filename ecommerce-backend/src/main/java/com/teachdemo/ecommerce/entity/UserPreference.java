package com.teachdemo.ecommerce.entity;

import java.math.BigDecimal;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class UserPreference {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String userId;

    private String preferredCategories;

    private String preferredDelivery;

    private BigDecimal budgetMin;

    private BigDecimal budgetMax;

    private Boolean invoiceRequired;

    protected UserPreference() {
    }

    public UserPreference(String userId, String preferredCategories, String preferredDelivery,
                          BigDecimal budgetMin, BigDecimal budgetMax, Boolean invoiceRequired) {
        this.userId = userId;
        this.preferredCategories = preferredCategories;
        this.preferredDelivery = preferredDelivery;
        this.budgetMin = budgetMin;
        this.budgetMax = budgetMax;
        this.invoiceRequired = invoiceRequired;
    }

    public void update(String preferredCategories, String preferredDelivery,
                       BigDecimal budgetMin, BigDecimal budgetMax, Boolean invoiceRequired) {
        this.preferredCategories = preferredCategories;
        this.preferredDelivery = preferredDelivery;
        this.budgetMin = budgetMin;
        this.budgetMax = budgetMax;
        this.invoiceRequired = invoiceRequired;
    }

    public Long getId() {
        return id;
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
