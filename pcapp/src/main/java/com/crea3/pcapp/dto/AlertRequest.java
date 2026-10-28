package com.crea3.pcapp.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

/** POST /api/alert 请求体。 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AlertRequest(
        @JsonProperty("device_id") String deviceId,
        @JsonProperty("timestamp") OffsetDateTime timestamp,
        @JsonProperty("type") String type,
        @JsonProperty("confidence") Double confidence,
        @JsonProperty("message") String message
) {
}
