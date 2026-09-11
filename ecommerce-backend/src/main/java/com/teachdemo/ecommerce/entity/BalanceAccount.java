package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "balance_account")
public class BalanceAccount {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String userId;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal availableBalance;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    protected BalanceAccount() {
    }

    public BalanceAccount(String userId, BigDecimal availableBalance, LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.userId = userId;
        this.availableBalance = availableBalance;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getId() {
        return id;
    }

    public String getUserId() {
        return userId;
    }

    public BigDecimal getAvailableBalance() {
        return availableBalance;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void updateBalance(BigDecimal availableBalance, LocalDateTime updatedAt) {
        this.availableBalance = availableBalance;
        this.updatedAt = updatedAt;
    }
}
