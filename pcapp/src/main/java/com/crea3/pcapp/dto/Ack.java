package com.crea3.pcapp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/** 接收类接口的统一响应。 */
public record Ack(
        @JsonProperty("ok") boolean ok,
        @JsonProperty("id") Long id,
        @JsonProperty("error") String error
) {
    public static Ack ok(Long id) {
        return new Ack(true, id, null);
    }

    public static Ack fail(String error) {
        return new Ack(false, null, error);
    }
}
