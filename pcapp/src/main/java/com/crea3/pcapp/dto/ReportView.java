package com.crea3.pcapp.dto;

import com.crea3.pcapp.entity.ReportEntity;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

/** 界面展示用的报告条目。 */
public record ReportView(
        @JsonProperty("id") Long id,
        @JsonProperty("device_id") String deviceId,
        @JsonProperty("reported_at") LocalDateTime reportedAt,
        @JsonProperty("status") String status,
        @JsonProperty("message") String message,
        @JsonProperty("received_at") LocalDateTime receivedAt
) {
    public static ReportView from(ReportEntity entity) {
        return new ReportView(
                entity.getId(),
                entity.getDeviceId(),
                entity.getReportedAt(),
                entity.getStatus(),
                entity.getMessage(),
                entity.getReceivedAt()
        );
    }
}
