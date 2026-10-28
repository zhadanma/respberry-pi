package com.crea3.pcapp.web;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/** 把监控端的 MJPEG 流原样转发给浏览器 <img>。 */
@RestController
public class PreviewController {

    private final String monitorBaseUrl;
    private final String apiToken;
    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    public PreviewController(
            @Value("${monitor.base-url}") String monitorBaseUrl,
            @Value("${app.api-token}") String apiToken
    ) {
        this.monitorBaseUrl = monitorBaseUrl.replaceAll("/+$", "");
        this.apiToken = apiToken;
    }

    @GetMapping("/ui/preview")
    public ResponseEntity<StreamingResponseBody> preview() {
        HttpRequest request = HttpRequest.newBuilder(URI.create(monitorBaseUrl + "/stream/video"))
                .header("X-Auth-Token", apiToken)
                .timeout(Duration.ofSeconds(10))
                .GET()
                .build();

        HttpResponse<InputStream> upstream;
        try {
            upstream = httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream());
        } catch (IOException | InterruptedException exception) {
            if (exception instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).build();
        }

        if (upstream.statusCode() != 200) {
            try {
                upstream.body().close();
            } catch (IOException ignored) {
                // 关闭失败无需处理，连接会被回收
            }
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).build();
        }

        String contentType = upstream.headers()
                .firstValue("Content-Type")
                .orElse("multipart/x-mixed-replace; boundary=frame");

        StreamingResponseBody body = outputStream -> {
            try (InputStream inputStream = upstream.body()) {
                inputStream.transferTo(outputStream);
                outputStream.flush();
            } catch (IOException exception) {
                // 客户端关闭页面时会中断，属正常现象
            }
        };

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(contentType))
                .header("Cache-Control", "no-store")
                .body(body);
    }
}
