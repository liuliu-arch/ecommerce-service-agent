package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDateTime;

@Schema(description = "Tracking event")
public class LogisticsEventResponse {

    @Schema(description = "Event time", example = "2026-04-24T08:30:00")
    private final LocalDateTime occurredAt;
    @Schema(description = "Event description", example = "The parcel left the Shanghai transfer center")
    private final String content;

    public LogisticsEventResponse(LocalDateTime occurredAt, String content) {
        this.occurredAt = occurredAt;
        this.content = content;
    }

    public LocalDateTime getOccurredAt() {
        return occurredAt;
    }

    public String getContent() {
        return content;
    }
}
