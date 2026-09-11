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
@Table(name = "balance_transaction")
public class BalanceTransaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String transactionNo;

    @Column(nullable = false)
    private String userId;

    private String orderNo;

    private String afterSaleNo;

    @Column(nullable = false)
    private String type;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal balanceBefore;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal balanceAfter;

    private String remark;

    private LocalDateTime createdAt;

    protected BalanceTransaction() {
    }

    public BalanceTransaction(String transactionNo, String userId, String orderNo, String afterSaleNo, String type,
                              BigDecimal amount, BigDecimal balanceBefore, BigDecimal balanceAfter,
                              String remark, LocalDateTime createdAt) {
        this.transactionNo = transactionNo;
        this.userId = userId;
        this.orderNo = orderNo;
        this.afterSaleNo = afterSaleNo;
        this.type = type;
        this.amount = amount;
        this.balanceBefore = balanceBefore;
        this.balanceAfter = balanceAfter;
        this.remark = remark;
        this.createdAt = createdAt;
    }

    public Long getId() {
        return id;
    }

    public String getTransactionNo() {
        return transactionNo;
    }

    public String getUserId() {
        return userId;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public String getAfterSaleNo() {
        return afterSaleNo;
    }

    public String getType() {
        return type;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public BigDecimal getBalanceBefore() {
        return balanceBefore;
    }

    public BigDecimal getBalanceAfter() {
        return balanceAfter;
    }

    public String getRemark() {
        return remark;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
}
