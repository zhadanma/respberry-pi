package com.crea3.pcapp.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

/** 监控端上报的异常警报。P4 起收到警报还会触发事件片段落盘。 */
@Entity
@Table(name = "alerts")
public class AlertEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, length = 64)
    private String deviceId;

    @Column(name = "reported_at", nullable = false)
    private LocalDateTime reportedAt;

    /** fall / inactivity / cry / abnormal_sound */
    @Column(name = "alert_type", nullable = false, length = 32)
    private String alertType;

    @Column(nullable = false)
    private double confidence;

    @Column(length = 500)
    private String message;

    @Column(name = "received_at", nullable = false)
    private LocalDateTime receivedAt;

    protected AlertEntity() {
    }

    public AlertEntity(String deviceId, LocalDateTime reportedAt, String alertType, double confidence, String message) {
        this.deviceId = deviceId;
        this.reportedAt = reportedAt;
        this.alertType = alertType;
        this.confidence = confidence;
        this.message = message;
        this.receivedAt = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public String getDeviceId() {
        return deviceId;
    }

    public LocalDateTime getReportedAt() {
        return reportedAt;
    }

    public String getAlertType() {
        return alertType;
    }

    public double getConfidence() {
        return confidence;
    }

    public String getMessage() {
        return message;
    }

    public LocalDateTime getReceivedAt() {
        return receivedAt;
    }
}
