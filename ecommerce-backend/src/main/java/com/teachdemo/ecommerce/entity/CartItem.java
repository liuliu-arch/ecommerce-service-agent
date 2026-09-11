package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "cart_item")
public class CartItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String userId;

    @Column(nullable = false)
    private Long productId;

    @Column(nullable = false)
    private Integer quantity;

    @Column(nullable = false)
    private Boolean selected;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    protected CartItem() {
    }

    public CartItem(String userId, Long productId, Integer quantity, Boolean selected,
                    LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.userId = userId;
        this.productId = productId;
        this.quantity = quantity;
        this.selected = selected;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getId() {
        return id;
    }

    public String getUserId() {
        return userId;
    }

    public Long getProductId() {
        return productId;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public Boolean getSelected() {
        return selected;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void update(Integer quantity, Boolean selected, LocalDateTime updatedAt) {
        if (quantity != null) {
            this.quantity = quantity;
        }
        if (selected != null) {
            this.selected = selected;
        }
        this.updatedAt = updatedAt;
    }
}
