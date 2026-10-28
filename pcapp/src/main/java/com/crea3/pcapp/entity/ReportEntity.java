package com.crea3.pcapp.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

/** 监控端上报的状态报告。 */
@Entity
@Table(name = "reports")
public class ReportEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "device_id", nullable = false, length = 64)
    private String deviceId;

    @Column(name = "reported_at", nullable = false)
    private LocalDateTime reportedAt;

    @Column(nullable = false, length = 16)
    private String status;

    @Column(length = 500)
    private String message;

    @Column(name = "received_at", nullable = false)
    private LocalDateTime receivedAt;

    protected ReportEntity() {
    }

    public ReportEntity(String deviceId, LocalDateTime reportedAt, String status, String message) {
        this.deviceId = deviceId;
        this.reportedAt = reportedAt;
        this.status = status;
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

    public String getStatus() {
        return status;
    }

    public String getMessage() {
        return message;
    }

    public LocalDateTime getReceivedAt() {
        return receivedAt;
    }
}
