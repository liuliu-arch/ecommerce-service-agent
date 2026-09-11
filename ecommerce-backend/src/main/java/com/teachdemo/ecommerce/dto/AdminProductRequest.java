package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;

public class AdminProductRequest {

    private String code;
    private String name;
    private String category;
    private String description;
    private BigDecimal price;
    private Integer stockQuantity;
    private String highlights;
    private String imageUrl;
    private Boolean supportsSevenDayReturn;
    private String afterSaleNote;
    private String scenarioTags;
    private String status;

    public String getCode() {
        return code;
    }

    public String getName() {
        return name;
    }

    public String getCategory() {
        return category;
    }

    public String getDescription() {
        return description;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public Integer getStockQuantity() {
        return stockQuantity;
    }

    public String getHighlights() {
        return highlights;
    }

    public String getImageUrl() {
        return imageUrl;
    }

    public Boolean getSupportsSevenDayReturn() {
        return supportsSevenDayReturn;
    }

    public String getAfterSaleNote() {
        return afterSaleNote;
    }

    public String getScenarioTags() {
        return scenarioTags;
    }

    public String getStatus() {
        return status;
    }
}
