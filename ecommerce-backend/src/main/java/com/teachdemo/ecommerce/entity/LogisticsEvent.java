package com.teachdemo.ecommerce.entity;

import java.time.LocalDateTime;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;

@Entity
public class LogisticsEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "logistics_id", nullable = false)
    private LogisticsInfo logisticsInfo;

    private LocalDateTime occurredAt;

    private String content;

    protected LogisticsEvent() {
    }

    public LogisticsEvent(LogisticsInfo logisticsInfo, LocalDateTime occurredAt, String content) {
        this.logisticsInfo = logisticsInfo;
        this.occurredAt = occurredAt;
        this.content = content;
    }

    public Long getId() {
        return id;
    }

    public LogisticsInfo getLogisticsInfo() {
        return logisticsInfo;
    }

    public LocalDateTime getOccurredAt() {
        return occurredAt;
    }

    public String getContent() {
        return content;
    }
}
