package com.crea3.pcapp.dto;

import com.crea3.pcapp.entity.DeviceConfigEntity;
import com.fasterxml.jackson.annotation.JsonProperty;

/** GET /api/config 响应体，同时也是界面读写配置的载体。 */
public record ConfigDto(
        @JsonProperty("version") int version,
        @JsonProperty("sleep_start") String sleepStart,
        @JsonProperty("sleep_end") String sleepEnd,
        @JsonProperty("inactivity_minutes") int inactivityMinutes,
        @JsonProperty("fall_confirm_seconds") int fallConfirmSeconds,
        @JsonProperty("report_interval_seconds") int reportIntervalSeconds,
        @JsonProperty("fall_confidence") double fallConfidence,
        @JsonProperty("sound_confidence") double soundConfidence,
        @JsonProperty("clip_pre_seconds") int clipPreSeconds,
        @JsonProperty("clip_post_seconds") int clipPostSeconds,
        @JsonProperty("clip_retention_days") int clipRetentionDays
) {
    public static ConfigDto from(DeviceConfigEntity entity) {
        return new ConfigDto(
                entity.getVersion(),
                entity.getSleepStart(),
                entity.getSleepEnd(),
                entity.getInactivityMinutes(),
                entity.getFallConfirmSeconds(),
                entity.getReportIntervalSeconds(),
                entity.getFallConfidence(),
                entity.getSoundConfidence(),
                entity.getClipPreSeconds(),
                entity.getClipPostSeconds(),
                entity.getClipRetentionDays()
        );
    }
}
