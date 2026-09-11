package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;

@Schema(description = "Product details")
public class ProductResponse {

    @Schema(description = "Product ID", example = "1")
    private final Long id;
    @Schema(description = "Product code", example = "SKU-1001")
    private final String code;
    @Schema(description = "Product name", example = "Noise Cancelling Headphones")
    private final String name;
    @Schema(description = "Category", example = "Accessories")
    private final String category;
    @Schema(description = "Description", example = "Lightweight headphones designed for commuting")
    private final String description;
    @Schema(description = "Price", example = "299.00")
    private final BigDecimal price;
    @Schema(description = "Available stock", example = "128")
    private final Integer stock;
    @Schema(description = "Selling points", example = "long battery life, ANC, lightweight")
    private final String highlights;
    @Schema(description = "Whether the product is active for sale", example = "true")
    private final Boolean active;
    @Schema(description = "Whether the product supports no-reason returns", example = "true")
    private final Boolean returnable;
    @Schema(description = "After-sale restriction summary", example = "opened custom products are not returnable")
    private final String afterSaleLimit;
    @Schema(description = "Comma-separated scenario tags", example = "通勤,差旅")
    private final String scenarioTags;
    @Schema(description = "Current active promotion facts")
    private final ProductPromotionResponse promotion;

    public ProductResponse(Long id, String code, String name, String category, String description,
                           BigDecimal price, Integer stock, String highlights) {
        this(id, code, name, category, description, price, stock, highlights, true, true, "", "");
    }

    public ProductResponse(Long id, String code, String name, String category, String description,
                           BigDecimal price, Integer stock, String highlights, Boolean active,
                           Boolean returnable, String afterSaleLimit, String scenarioTags) {
        this(id, code, name, category, description, price, stock, highlights, active, returnable,
            afterSaleLimit, scenarioTags, null);
    }

    public ProductResponse(Long id, String code, String name, String category, String description,
                           BigDecimal price, Integer stock, String highlights, Boolean active,
                           Boolean returnable, String afterSaleLimit, String scenarioTags,
                           ProductPromotionResponse promotion) {
        this.id = id;
        this.code = code;
        this.name = name;
        this.category = category;
        this.description = description;
        this.price = price;
        this.stock = stock;
        this.highlights = highlights;
        this.active = active;
        this.returnable = returnable;
        this.afterSaleLimit = afterSaleLimit;
        this.scenarioTags = scenarioTags;
        this.promotion = promotion;
    }

    public Long getId() {
        return id;
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

    public Integer getStock() {
        return stock;
    }

    public String getHighlights() {
        return highlights;
    }

    public Boolean getActive() {
        return active;
    }

    public Boolean getReturnable() {
        return returnable;
    }

    public String getAfterSaleLimit() {
        return afterSaleLimit;
    }

    public String getScenarioTags() {
        return scenarioTags;
    }

    public ProductPromotionResponse getPromotion() {
        return promotion;
    }
}
