package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String code;

    @Column(nullable = false)
    private String name;

    private String category;

    @Column(length = 1000)
    private String description;

    private BigDecimal price;

    private Integer stock;

    private String highlights;

    private Boolean active;

    private Boolean returnable;

    private String afterSaleLimit;

    private String scenarioTags;

    private String imageUrl;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    protected Product() {
    }

    public Product(String code, String name, String category, String description,
                   BigDecimal price, Integer stock, String highlights) {
        this(code, name, category, description, price, stock, highlights, true, true, "", "");
    }

    public Product(String code, String name, String category, String description,
                   BigDecimal price, Integer stock, String highlights, Boolean active,
                   Boolean returnable, String afterSaleLimit, String scenarioTags) {
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
        this.imageUrl = "";
        this.createdAt = LocalDateTime.now();
        this.updatedAt = this.createdAt;
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

    public void decreaseStock(int quantity) {
        if (stock == null || stock < quantity) {
            throw new IllegalArgumentException("Stock is not enough for product: " + id);
        }
        this.stock = stock - quantity;
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

    public String getImageUrl() {
        return imageUrl;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void updateCatalogInfo(String name, String category, String description, BigDecimal price,
                                  Integer stock, String imageUrl, Boolean returnable,
                                  String afterSaleLimit) {
        this.name = name;
        this.category = category;
        this.description = description;
        this.price = price;
        this.stock = stock;
        this.imageUrl = imageUrl;
        this.returnable = returnable;
        this.afterSaleLimit = afterSaleLimit;
        this.updatedAt = LocalDateTime.now();
    }

    public void updateAdminFields(String name, String category, String description, BigDecimal price,
                                  Integer stock, String highlights, Boolean returnable,
                                  String afterSaleLimit, String scenarioTags, String imageUrl) {
        this.name = name;
        this.category = category;
        this.description = description;
        this.price = price;
        this.stock = stock;
        this.highlights = highlights;
        this.returnable = returnable;
        this.afterSaleLimit = afterSaleLimit;
        this.scenarioTags = scenarioTags;
        this.imageUrl = imageUrl;
        this.updatedAt = LocalDateTime.now();
    }

    public void updateStock(Integer stock) {
        this.stock = stock;
        this.updatedAt = LocalDateTime.now();
    }

    public void publish() {
        this.active = true;
        this.updatedAt = LocalDateTime.now();
    }

    public void unpublish() {
        this.active = false;
        this.updatedAt = LocalDateTime.now();
    }
}
