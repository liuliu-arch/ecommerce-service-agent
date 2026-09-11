package com.teachdemo.ecommerce.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "order_header")
public class OrderEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String orderNo;

    private String customerName;

    private String status;

    private String paymentStatus;

    private BigDecimal totalAmount;

    private LocalDateTime createdAt;

    private String userId;

    private LocalDateTime shippedAt;

    private LocalDateTime deliveredAt;

    private Boolean hasAfterSaleRequest;

    private Boolean cancelAllowed;

    private String fulfillmentStatus;

    private String logisticsNo;

    private String remark;

    private LocalDateTime paidAt;

    protected OrderEntity() {
    }

    public OrderEntity(String orderNo, String customerName, String status, String paymentStatus,
                       BigDecimal totalAmount, LocalDateTime createdAt) {
        this(orderNo, customerName, status, paymentStatus, totalAmount, createdAt, null, null, null, false, false);
    }

    public OrderEntity(String orderNo, String customerName, String status, String paymentStatus,
                       BigDecimal totalAmount, LocalDateTime createdAt, String userId,
                       LocalDateTime shippedAt, LocalDateTime deliveredAt,
                       Boolean hasAfterSaleRequest, Boolean cancelAllowed) {
        this.orderNo = orderNo;
        this.customerName = customerName;
        this.status = status;
        this.paymentStatus = paymentStatus;
        this.totalAmount = totalAmount;
        this.createdAt = createdAt;
        this.userId = userId;
        this.shippedAt = shippedAt;
        this.deliveredAt = deliveredAt;
        this.hasAfterSaleRequest = hasAfterSaleRequest;
        this.cancelAllowed = cancelAllowed;
    }

    public OrderEntity(String orderNo, String customerName, String status, String paymentStatus,
                       BigDecimal totalAmount, LocalDateTime createdAt, String userId,
                       Boolean hasAfterSaleRequest, Boolean cancelAllowed, String remark) {
        this.orderNo = orderNo;
        this.customerName = customerName;
        this.status = status;
        this.paymentStatus = paymentStatus;
        this.totalAmount = totalAmount;
        this.createdAt = createdAt;
        this.userId = userId;
        this.shippedAt = null;
        this.deliveredAt = null;
        this.hasAfterSaleRequest = hasAfterSaleRequest;
        this.cancelAllowed = cancelAllowed;
        this.fulfillmentStatus = "UNSHIPPED";
        this.remark = remark;
        this.paidAt = null;
    }

    public Long getId() {
        return id;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public String getCustomerName() {
        return customerName;
    }

    public String getStatus() {
        return status;
    }

    public String getPaymentStatus() {
        return paymentStatus;
    }

    public BigDecimal getTotalAmount() {
        return totalAmount;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public String getUserId() {
        return userId;
    }

    public LocalDateTime getShippedAt() {
        return shippedAt;
    }

    public LocalDateTime getDeliveredAt() {
        return deliveredAt;
    }

    public Boolean getHasAfterSaleRequest() {
        return hasAfterSaleRequest;
    }

    public Boolean getCancelAllowed() {
        return cancelAllowed;
    }

    public String getFulfillmentStatus() {
        if (fulfillmentStatus != null) {
            return fulfillmentStatus;
        }
        if ("SHIPPED".equals(status)) {
            return "SHIPPED";
        }
        if ("DELIVERED".equals(status) || "SIGNED".equals(status) || "COMPLETED".equals(status)) {
            return "DELIVERED";
        }
        return "UNSHIPPED";
    }

    public String getLogisticsNo() {
        return logisticsNo;
    }

    public String getRemark() {
        return remark;
    }

    public LocalDateTime getPaidAt() {
        return paidAt;
    }

    public void markPaid(LocalDateTime paidAt) {
        this.status = "PAID_PENDING_SHIPMENT";
        this.paymentStatus = "PAID";
        this.fulfillmentStatus = "UNSHIPPED";
        this.paidAt = paidAt;
    }

    public void updateAdminFields(String status, String fulfillmentStatus, String logisticsNo,
                                  String remark, LocalDateTime now) {
        if (status != null && !status.isBlank()) {
            this.status = status;
        }
        if (fulfillmentStatus != null && !fulfillmentStatus.isBlank()) {
            this.fulfillmentStatus = fulfillmentStatus;
            if ("SHIPPED".equals(fulfillmentStatus) && this.shippedAt == null) {
                this.shippedAt = now;
            }
        }
        if (logisticsNo != null) {
            this.logisticsNo = logisticsNo;
        }
        if (remark != null) {
            this.remark = remark;
        }
    }

    public void markAfterSaleRequested() {
        this.hasAfterSaleRequest = true;
    }
}
