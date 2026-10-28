package com.crea3.pcapp.dto;

import com.crea3.pcapp.entity.AlertEntity;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

/** 界面展示用的警报条目。 */
public record AlertView(
        @JsonProperty("id") Long id,
        @JsonProperty("device_id") String deviceId,
        @JsonProperty("reported_at") LocalDateTime reportedAt,
        @JsonProperty("type") String type,
        @JsonProperty("confidence") double confidence,
        @JsonProperty("message") String message,
        @JsonProperty("received_at") LocalDateTime receivedAt
) {
    public static AlertView from(AlertEntity entity) {
        return new AlertView(
                entity.getId(),
                entity.getDeviceId(),
                entity.getReportedAt(),
                entity.getAlertType(),
                entity.getConfidence(),
                entity.getMessage(),
                entity.getReceivedAt()
        );
    }
}
