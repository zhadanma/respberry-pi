package com.crea3.pcapp.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

/** POST /api/report 请求体。 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ReportRequest(
        @JsonProperty("device_id") String deviceId,
        @JsonProperty("timestamp") OffsetDateTime timestamp,
        @JsonProperty("status") String status,
        @JsonProperty("message") String message
) {
}
