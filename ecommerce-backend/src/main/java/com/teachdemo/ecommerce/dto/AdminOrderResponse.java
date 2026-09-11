package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public class AdminOrderResponse {

    private final String orderNo;
    private final String userId;
    private final String userNickname;
    private final String userMobile;
    private final String orderStatus;
    private final String paymentStatus;
    private final String fulfillmentStatus;
    private final BigDecimal totalAmount;
    private final String logisticsNo;
    private final String remark;
    private final LocalDateTime createdAt;
    private final LocalDateTime paidAt;
    private final LocalDateTime shippedAt;
    private final LocalDateTime signedAt;
    private final List<OrderItemResponse> items;
    private final List<LogisticsEventResponse> logisticsEvents;
    private final List<AfterSaleRequestResponse> afterSaleRequests;

    public AdminOrderResponse(String orderNo, String userId, String userNickname, String userMobile,
                              String orderStatus, String paymentStatus, String fulfillmentStatus,
                              BigDecimal totalAmount, String logisticsNo, String remark,
                              LocalDateTime createdAt, LocalDateTime paidAt, LocalDateTime shippedAt,
                              LocalDateTime signedAt, List<OrderItemResponse> items,
                              List<LogisticsEventResponse> logisticsEvents,
                              List<AfterSaleRequestResponse> afterSaleRequests) {
        this.orderNo = orderNo;
        this.userId = userId;
        this.userNickname = userNickname;
        this.userMobile = userMobile;
        this.orderStatus = orderStatus;
        this.paymentStatus = paymentStatus;
        this.fulfillmentStatus = fulfillmentStatus;
        this.totalAmount = totalAmount;
        this.logisticsNo = logisticsNo;
        this.remark = remark;
        this.createdAt = createdAt;
        this.paidAt = paidAt;
        this.shippedAt = shippedAt;
        this.signedAt = signedAt;
        this.items = items;
        this.logisticsEvents = logisticsEvents;
        this.afterSaleRequests = afterSaleRequests;
    }

    public String getOrderNo() { return orderNo; }
    public String getUserId() { return userId; }
    public String getUserNickname() { return userNickname; }
    public String getUserMobile() { return userMobile; }
    public String getOrderStatus() { return orderStatus; }
    public String getPaymentStatus() { return paymentStatus; }
    public String getFulfillmentStatus() { return fulfillmentStatus; }
    public BigDecimal getTotalAmount() { return totalAmount; }
    public String getLogisticsNo() { return logisticsNo; }
    public String getRemark() { return remark; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getPaidAt() { return paidAt; }
    public LocalDateTime getShippedAt() { return shippedAt; }
    public LocalDateTime getSignedAt() { return signedAt; }
    public List<OrderItemResponse> getItems() { return items; }
    public List<LogisticsEventResponse> getLogisticsEvents() { return logisticsEvents; }
    public List<AfterSaleRequestResponse> getAfterSaleRequests() { return afterSaleRequests; }
}
