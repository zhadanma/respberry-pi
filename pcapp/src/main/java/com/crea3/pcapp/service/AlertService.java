package com.crea3.pcapp.service;

import com.crea3.pcapp.dto.AlertRequest;
import com.crea3.pcapp.entity.AlertEntity;
import com.crea3.pcapp.repository.AlertRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Set;

@Service
public class AlertService {

    private static final Set<String> ALERT_TYPES = Set.of("fall", "inactivity", "cry", "abnormal_sound");

    private final AlertRepository repository;

    public AlertService(AlertRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public AlertEntity save(AlertRequest request) {
        String deviceId = ReportService.requireText(request.deviceId(), "device_id");
        String type = ReportService.requireText(request.type(), "type");
        if (!ALERT_TYPES.contains(type)) {
            throw new IllegalArgumentException("type 必须是 " + ALERT_TYPES);
        }
        double confidence = request.confidence() == null ? 0.0 : request.confidence();
        if (confidence < 0.0 || confidence > 1.0) {
            throw new IllegalArgumentException("confidence 必须位于 0~1");
        }
        String message = request.message() == null ? "" : request.message();
        if (message.length() > 500) {
            throw new IllegalArgumentException("message 超过 500 字符");
        }
        AlertEntity entity = new AlertEntity(
                deviceId,
                ReportService.toLocal(request.timestamp()),
                type,
                confidence,
                message
        );
        return repository.save(entity);
    }

    @Transactional(readOnly = true)
    public List<AlertEntity> recent() {
        return repository.findTop100ByOrderByReceivedAtDesc();
    }

    @Transactional(readOnly = true)
    public long count() {
        return repository.count();
    }
}
