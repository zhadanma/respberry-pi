package com.crea3.pcapp.web;

import com.crea3.pcapp.dto.Ack;
import com.crea3.pcapp.dto.AlertRequest;
import com.crea3.pcapp.dto.ConfigDto;
import com.crea3.pcapp.dto.ReportRequest;
import com.crea3.pcapp.entity.AlertEntity;
import com.crea3.pcapp.entity.ReportEntity;
import com.crea3.pcapp.service.AlertService;
import com.crea3.pcapp.service.ConfigService;
import com.crea3.pcapp.service.ReportService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 监控端调用的接口，全部位于 /api/**，由 ApiTokenFilter 鉴权。 */
@RestController
@RequestMapping("/api")
public class ApiController {

    private final ReportService reportService;
    private final AlertService alertService;
    private final ConfigService configService;

    public ApiController(ReportService reportService, AlertService alertService, ConfigService configService) {
        this.reportService = reportService;
        this.alertService = alertService;
        this.configService = configService;
    }

    @PostMapping("/report")
    public Ack report(@RequestBody ReportRequest request) {
        ReportEntity saved = reportService.save(request);
        return Ack.ok(saved.getId());
    }

    @PostMapping("/alert")
    public Ack alert(@RequestBody AlertRequest request) {
        AlertEntity saved = alertService.save(request);
        return Ack.ok(saved.getId());
    }

    @GetMapping("/config")
    public ConfigDto config() {
        return ConfigDto.from(configService.get());
    }
}
