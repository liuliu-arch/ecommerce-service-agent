package com.teachdemo.ecommerce.entity;

import java.time.LocalDate;
import java.time.LocalDateTime;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToOne;

@Entity
public class LogisticsInfo {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false, unique = true)
    private OrderEntity orderEntity;

    private String company;

    private String trackingNo;

    private String status;

    private LocalDate estimatedDelivery;

    private String latestUpdate;

    private LocalDateTime deliveredAt;

    private String exceptionReason;

    protected LogisticsInfo() {
    }

    public LogisticsInfo(OrderEntity orderEntity, String company, String trackingNo, String status,
                         LocalDate estimatedDelivery, String latestUpdate) {
        this(orderEntity, company, trackingNo, status, estimatedDelivery, latestUpdate, null, null);
    }

    public LogisticsInfo(OrderEntity orderEntity, String company, String trackingNo, String status,
                         LocalDate estimatedDelivery, String latestUpdate, LocalDateTime deliveredAt,
                         String exceptionReason) {
        this.orderEntity = orderEntity;
        this.company = company;
        this.trackingNo = trackingNo;
        this.status = status;
        this.estimatedDelivery = estimatedDelivery;
        this.latestUpdate = latestUpdate;
        this.deliveredAt = deliveredAt;
        this.exceptionReason = exceptionReason;
    }

    public Long getId() {
        return id;
    }

    public OrderEntity getOrderEntity() {
        return orderEntity;
    }

    public String getCompany() {
        return company;
    }

    public String getTrackingNo() {
        return trackingNo;
    }

    public String getStatus() {
        return status;
    }

    public LocalDate getEstimatedDelivery() {
        return estimatedDelivery;
    }

    public String getLatestUpdate() {
        return latestUpdate;
    }

    public LocalDateTime getDeliveredAt() {
        return deliveredAt;
    }

    public String getExceptionReason() {
        return exceptionReason;
    }
}
