package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public class BalanceTransactionResponse {

    private final String transactionNo;
    private final String type;
    private final BigDecimal amount;
    private final BigDecimal balanceBefore;
    private final BigDecimal balanceAfter;
    private final String orderNo;
    private final String afterSaleNo;
    private final String remark;
    private final LocalDateTime createdAt;

    public BalanceTransactionResponse(String transactionNo, String type, BigDecimal amount,
                                      BigDecimal balanceBefore, BigDecimal balanceAfter, String orderNo,
                                      String afterSaleNo, String remark, LocalDateTime createdAt) {
        this.transactionNo = transactionNo;
        this.type = type;
        this.amount = amount;
        this.balanceBefore = balanceBefore;
        this.balanceAfter = balanceAfter;
        this.orderNo = orderNo;
        this.afterSaleNo = afterSaleNo;
        this.remark = remark;
        this.createdAt = createdAt;
    }

    public String getTransactionNo() { return transactionNo; }
    public String getType() { return type; }
    public BigDecimal getAmount() { return amount; }
    public BigDecimal getBalanceBefore() { return balanceBefore; }
    public BigDecimal getBalanceAfter() { return balanceAfter; }
    public String getOrderNo() { return orderNo; }
    public String getAfterSaleNo() { return afterSaleNo; }
    public String getRemark() { return remark; }
    public LocalDateTime getCreatedAt() { return createdAt; }
}
