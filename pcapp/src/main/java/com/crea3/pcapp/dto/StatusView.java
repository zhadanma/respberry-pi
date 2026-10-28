package com.crea3.pcapp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

/** GET /ui/status 响应：界面顶部状态条。 */
public record StatusView(
        @JsonProperty("monitor_online") boolean monitorOnline,
        @JsonProperty("last_report_at") LocalDateTime lastReportAt,
        @JsonProperty("report_count") long reportCount,
        @JsonProperty("alert_count") long alertCount,
        @JsonProperty("config_version") int configVersion
) {
}
