package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Schema(description = "Logistics details")
public class LogisticsResponse {

    @Schema(description = "Carrier", example = "SF Express")
    private final String company;
    @Schema(description = "Tracking number", example = "SF1234567890")
    private final String trackingNo;
    @Schema(description = "Logistics status", example = "IN_TRANSIT")
    private final String status;
    @Schema(description = "Estimated delivery date", example = "2026-04-25")
    private final LocalDate estimatedDelivery;
    @Schema(description = "Latest update", example = "Parcel arrived at the Shanghai transfer center")
    private final String latestUpdate;
    @Schema(description = "Delivery time", example = "2026-04-23T10:00:00")
    private final LocalDateTime deliveredAt;
    @Schema(description = "Exception reason when logistics status is EXCEPTION", example = "Address information needs confirmation")
    private final String exceptionReason;
    @Schema(description = "Tracking events")
    private final List<LogisticsEventResponse> events;

    public LogisticsResponse(String company, String trackingNo, String status, LocalDate estimatedDelivery,
                             String latestUpdate, List<LogisticsEventResponse> events) {
        this(company, trackingNo, status, estimatedDelivery, latestUpdate, null, null, events);
    }

    public LogisticsResponse(String company, String trackingNo, String status, LocalDate estimatedDelivery,
                             String latestUpdate, LocalDateTime deliveredAt, String exceptionReason,
                             List<LogisticsEventResponse> events) {
        this.company = company;
        this.trackingNo = trackingNo;
        this.status = status;
        this.estimatedDelivery = estimatedDelivery;
        this.latestUpdate = latestUpdate;
        this.deliveredAt = deliveredAt;
        this.exceptionReason = exceptionReason;
        this.events = events;
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

    public List<LogisticsEventResponse> getEvents() {
        return events;
    }
}
