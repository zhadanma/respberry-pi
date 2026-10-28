package com.crea3.pcapp.service;

import com.crea3.pcapp.dto.ConfigDto;
import com.crea3.pcapp.dto.ConfigUpdateRequest;
import com.crea3.pcapp.entity.DeviceConfigEntity;
import com.crea3.pcapp.repository.DeviceConfigRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.regex.Pattern;

@Service
public class ConfigService {

    private static final Pattern HH_MM = Pattern.compile("^([01]\\d|2[0-3]):[0-5]\\d$");

    private final DeviceConfigRepository repository;

    public ConfigService(DeviceConfigRepository repository) {
        this.repository = repository;
    }

    @PostConstruct
    @Transactional
    public void initialize() {
        if (repository.findById(DeviceConfigEntity.SINGLETON_ID).isEmpty()) {
            repository.save(DeviceConfigEntity.defaults());
        }
    }

    @Transactional(readOnly = true)
    public DeviceConfigEntity get() {
        return repository.findById(DeviceConfigEntity.SINGLETON_ID)
                .orElseThrow(() -> new IllegalStateException("配置行缺失，重启应用以重新初始化"));
    }

    @Transactional
    public ConfigDto update(ConfigUpdateRequest request) {
        DeviceConfigEntity current = get();

        String sleepStart = timeOrCurrent(request.sleepStart(), current.getSleepStart(), "sleep_start");
        String sleepEnd = timeOrCurrent(request.sleepEnd(), current.getSleepEnd(), "sleep_end");
        int inactivityMinutes = intOrCurrent(request.inactivityMinutes(), current.getInactivityMinutes(), 1, 1440, "inactivity_minutes");
        int fallConfirmSeconds = intOrCurrent(request.fallConfirmSeconds(), current.getFallConfirmSeconds(), 1, 600, "fall_confirm_seconds");
        int reportIntervalSeconds = intOrCurrent(request.reportIntervalSeconds(), current.getReportIntervalSeconds(), 1, 86400, "report_interval_seconds");
        double fallConfidence = doubleOrCurrent(request.fallConfidence(), current.getFallConfidence(), "fall_confidence");
        double soundConfidence = doubleOrCurrent(request.soundConfidence(), current.getSoundConfidence(), "sound_confidence");
        int clipPreSeconds = intOrCurrent(request.clipPreSeconds(), current.getClipPreSeconds(), 0, 600, "clip_pre_seconds");
        int clipPostSeconds = intOrCurrent(request.clipPostSeconds(), current.getClipPostSeconds(), 0, 600, "clip_post_seconds");
        int clipRetentionDays = intOrCurrent(request.clipRetentionDays(), current.getClipRetentionDays(), 1, 3650, "clip_retention_days");

        current.apply(
                sleepStart, sleepEnd, inactivityMinutes, fallConfirmSeconds, reportIntervalSeconds,
                fallConfidence, soundConfidence, clipPreSeconds, clipPostSeconds, clipRetentionDays
        );
        return ConfigDto.from(repository.save(current));
    }

    private static String timeOrCurrent(String value, String current, String field) {
        if (value == null) {
            return current;
        }
        if (!HH_MM.matcher(value).matches()) {
            throw new IllegalArgumentException(field + " 必须是 HH:mm 格式");
        }
        return value;
    }

    private static int intOrCurrent(Integer value, int current, int low, int high, String field) {
        if (value == null) {
            return current;
        }
        if (value < low || value > high) {
            throw new IllegalArgumentException(field + " 必须位于 " + low + "~" + high);
        }
        return value;
    }

    private static double doubleOrCurrent(Double value, double current, String field) {
        if (value == null) {
            return current;
        }
        if (value < 0.0 || value > 1.0) {
            throw new IllegalArgumentException(field + " 必须位于 0~1");
        }
        return value;
    }
}
