package com.crea3.pcapp.web;

import com.crea3.pcapp.dto.AlertView;
import com.crea3.pcapp.dto.ConfigDto;
import com.crea3.pcapp.dto.ConfigUpdateRequest;
import com.crea3.pcapp.dto.ReportView;
import com.crea3.pcapp.dto.StatusView;
import com.crea3.pcapp.entity.DeviceConfigEntity;
import com.crea3.pcapp.entity.ReportEntity;
import com.crea3.pcapp.service.AlertService;
import com.crea3.pcapp.service.ConfigService;
import com.crea3.pcapp.service.ReportService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

/** 浏览器界面调用的接口，只在本机页面内使用。 */
@RestController
@RequestMapping("/ui")
public class UiApiController {

    private final ReportService reportService;
    private final AlertService alertService;
    private final ConfigService configService;

    public UiApiController(ReportService reportService, AlertService alertService, ConfigService configService) {
        this.reportService = reportService;
        this.alertService = alertService;
        this.configService = configService;
    }

    @GetMapping("/reports")
    public List<ReportView> reports() {
        return reportService.recent().stream().map(ReportView::from).toList();
    }

    @GetMapping("/alerts")
    public List<AlertView> alerts() {
        return alertService.recent().stream().map(AlertView::from).toList();
    }

    @GetMapping("/config")
    public ConfigDto config() {
        return ConfigDto.from(configService.get());
    }

    @PutMapping("/config")
    public ConfigDto updateConfig(@RequestBody ConfigUpdateRequest request) {
        return configService.update(request);
    }

    @GetMapping("/status")
    public StatusView status() {
        ReportEntity latest = reportService.latest();
        DeviceConfigEntity config = configService.get();
        long onlineWindowSeconds = Math.max(30L, 2L * config.getReportIntervalSeconds());
        boolean online = latest != null
                && Duration.between(latest.getReceivedAt(), LocalDateTime.now()).getSeconds() <= onlineWindowSeconds;
        return new StatusView(
                online,
                latest == null ? null : latest.getReceivedAt(),
                reportService.count(),
                alertService.count(),
                config.getVersion()
        );
    }
}
