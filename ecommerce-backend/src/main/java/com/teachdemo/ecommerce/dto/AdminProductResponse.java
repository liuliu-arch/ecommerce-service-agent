package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class AdminProductResponse {

    private final Long productId;
    private final String code;
    private final String name;
    private final String category;
    private final String description;
    private final BigDecimal price;
    private final Integer stockQuantity;
    private final String highlights;
    private final String status;
    private final String imageUrl;
    private final Boolean supportsSevenDayReturn;
    private final String afterSaleNote;
    private final String scenarioTags;
    private final LocalDateTime createdAt;
    private final LocalDateTime updatedAt;

    public AdminProductResponse(Long productId, String code, String name, String category, String description,
                                BigDecimal price, Integer stockQuantity, String highlights, String status,
                                String imageUrl, Boolean supportsSevenDayReturn, String afterSaleNote,
                                String scenarioTags, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.productId = productId;
        this.code = code;
        this.name = name;
        this.category = category;
        this.description = description;
        this.price = price;
        this.stockQuantity = stockQuantity;
        this.highlights = highlights;
        this.status = status;
        this.imageUrl = imageUrl;
        this.supportsSevenDayReturn = supportsSevenDayReturn;
        this.afterSaleNote = afterSaleNote;
        this.scenarioTags = scenarioTags;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getProductId() {
        return productId;
    }

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

    public String getStatus() {
        return status;
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

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
}
