package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Schema(description = "Order details")
public class OrderResponse {

    @Schema(description = "Order number", example = "SO20260420103000001-a1000001")
    private final String orderNo;
    @Schema(description = "Customer name", example = "Alice")
    private final String customerName;
    @Schema(description = "Order status", example = "SHIPPED")
    private final String status;
    @Schema(description = "Payment status", example = "PAID")
    private final String paymentStatus;
    @Schema(description = "Total amount", example = "399.00")
    private final BigDecimal totalAmount;
    @Schema(description = "Creation time", example = "2026-04-20T10:15:30")
    private final LocalDateTime createdAt;
    @Schema(description = "User ID", example = "U1001")
    private final String userId;
    @Schema(description = "Shipment time", example = "2026-04-20T14:00:00")
    private final LocalDateTime shippedAt;
    @Schema(description = "Delivery time", example = "2026-04-23T10:00:00")
    private final LocalDateTime deliveredAt;
    @Schema(description = "Whether this order already has after-sale request", example = "false")
    private final Boolean hasAfterSaleRequest;
    @Schema(description = "Whether this order can be canceled directly", example = "true")
    private final Boolean cancelAllowed;
    @Schema(description = "Order items")
    private final List<OrderItemResponse> items;

    public OrderResponse(String orderNo, String customerName, String status, String paymentStatus,
                         BigDecimal totalAmount, LocalDateTime createdAt, List<OrderItemResponse> items) {
        this(orderNo, customerName, status, paymentStatus, totalAmount, createdAt, null, null, null, false, false, items);
    }

    public OrderResponse(String orderNo, String customerName, String status, String paymentStatus,
                         BigDecimal totalAmount, LocalDateTime createdAt, String userId,
                         LocalDateTime shippedAt, LocalDateTime deliveredAt,
                         Boolean hasAfterSaleRequest, Boolean cancelAllowed, List<OrderItemResponse> items) {
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
        this.items = items;
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

    public List<OrderItemResponse> getItems() {
        return items;
    }
}
