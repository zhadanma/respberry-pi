package com.crea3.pcapp.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** PUT /ui/config 请求体；字段为 null 表示不修改。 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ConfigUpdateRequest(
        @JsonProperty("sleep_start") String sleepStart,
        @JsonProperty("sleep_end") String sleepEnd,
        @JsonProperty("inactivity_minutes") Integer inactivityMinutes,
        @JsonProperty("fall_confirm_seconds") Integer fallConfirmSeconds,
        @JsonProperty("report_interval_seconds") Integer reportIntervalSeconds,
        @JsonProperty("fall_confidence") Double fallConfidence,
        @JsonProperty("sound_confidence") Double soundConfidence,
        @JsonProperty("clip_pre_seconds") Integer clipPreSeconds,
        @JsonProperty("clip_post_seconds") Integer clipPostSeconds,
        @JsonProperty("clip_retention_days") Integer clipRetentionDays
) {
}
