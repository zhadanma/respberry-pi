package com.crea3.pcapp.service;

import com.crea3.pcapp.dto.ReportRequest;
import com.crea3.pcapp.entity.ReportEntity;
import com.crea3.pcapp.repository.ReportRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.List;

@Service
public class ReportService {

    private final ReportRepository repository;

    public ReportService(ReportRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public ReportEntity save(ReportRequest request) {
        String deviceId = requireText(request.deviceId(), "device_id");
        String status = request.status() == null || request.status().isBlank() ? "normal" : request.status();
        if (!status.equals("normal") && !status.equals("alert")) {
            throw new IllegalArgumentException("status 只能是 normal 或 alert");
        }
        String message = request.message() == null ? "" : request.message();
        if (message.length() > 500) {
            throw new IllegalArgumentException("message 超过 500 字符");
        }
        ReportEntity entity = new ReportEntity(deviceId, toLocal(request.timestamp()), status, message);
        return repository.save(entity);
    }

    @Transactional(readOnly = true)
    public List<ReportEntity> recent() {
        return repository.findTop100ByOrderByReceivedAtDesc();
    }

    @Transactional(readOnly = true)
    public ReportEntity latest() {
        return repository.findTop1ByOrderByReceivedAtDesc().orElse(null);
    }

    @Transactional(readOnly = true)
    public long count() {
        return repository.count();
    }

    static String requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " 不能为空");
        }
        return value.trim();
    }

    static LocalDateTime toLocal(OffsetDateTime timestamp) {
        return (timestamp == null ? OffsetDateTime.now() : timestamp)
                .atZoneSameInstant(ZoneId.systemDefault())
                .toLocalDateTime();
    }
}
