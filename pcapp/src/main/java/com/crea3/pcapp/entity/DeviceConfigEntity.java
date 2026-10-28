package com.crea3.pcapp.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

/** 由 PC 端维护、监控端定期拉取的运行期参数（单行表，id 固定为 1）。 */
@Entity
@Table(name = "device_config")
public class DeviceConfigEntity {

    public static final long SINGLETON_ID = 1L;

    @Id
    private Long id = SINGLETON_ID;

    @Column(nullable = false)
    private int version;

    @Column(name = "sleep_start", nullable = false, length = 5)
    private String sleepStart;

    @Column(name = "sleep_end", nullable = false, length = 5)
    private String sleepEnd;

    @Column(name = "inactivity_minutes", nullable = false)
    private int inactivityMinutes;

    @Column(name = "fall_confirm_seconds", nullable = false)
    private int fallConfirmSeconds;

    @Column(name = "report_interval_seconds", nullable = false)
    private int reportIntervalSeconds;

    @Column(name = "fall_confidence", nullable = false)
    private double fallConfidence;

    @Column(name = "sound_confidence", nullable = false)
    private double soundConfidence;

    @Column(name = "clip_pre_seconds", nullable = false)
    private int clipPreSeconds;

    @Column(name = "clip_post_seconds", nullable = false)
    private int clipPostSeconds;

    @Column(name = "clip_retention_days", nullable = false)
    private int clipRetentionDays;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    protected DeviceConfigEntity() {
    }

    public static DeviceConfigEntity defaults() {
        DeviceConfigEntity config = new DeviceConfigEntity();
        config.version = 1;
        config.sleepStart = "22:00";
        config.sleepEnd = "07:00";
        config.inactivityMinutes = 30;
        config.fallConfirmSeconds = 5;
        config.reportIntervalSeconds = 3600;
        config.fallConfidence = 0.6;
        config.soundConfidence = 0.5;
        config.clipPreSeconds = 30;
        config.clipPostSeconds = 30;
        config.clipRetentionDays = 30;
        config.updatedAt = LocalDateTime.now();
        return config;
    }

    public Long getId() {
        return id;
    }

    public int getVersion() {
        return version;
    }

    public String getSleepStart() {
        return sleepStart;
    }

    public String getSleepEnd() {
        return sleepEnd;
    }

    public int getInactivityMinutes() {
        return inactivityMinutes;
    }

    public int getFallConfirmSeconds() {
        return fallConfirmSeconds;
    }

    public int getReportIntervalSeconds() {
        return reportIntervalSeconds;
    }

    public double getFallConfidence() {
        return fallConfidence;
    }

    public double getSoundConfidence() {
        return soundConfidence;
    }

    public int getClipPreSeconds() {
        return clipPreSeconds;
    }

    public int getClipPostSeconds() {
        return clipPostSeconds;
    }

    public int getClipRetentionDays() {
        return clipRetentionDays;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    /** 整体覆盖参数并把版本号 +1，供监控端识别变更。 */
    public void apply(String sleepStart, String sleepEnd, int inactivityMinutes, int fallConfirmSeconds,
                      int reportIntervalSeconds, double fallConfidence, double soundConfidence,
                      int clipPreSeconds, int clipPostSeconds, int clipRetentionDays) {
        this.sleepStart = sleepStart;
        this.sleepEnd = sleepEnd;
        this.inactivityMinutes = inactivityMinutes;
        this.fallConfirmSeconds = fallConfirmSeconds;
        this.reportIntervalSeconds = reportIntervalSeconds;
        this.fallConfidence = fallConfidence;
        this.soundConfidence = soundConfidence;
        this.clipPreSeconds = clipPreSeconds;
        this.clipPostSeconds = clipPostSeconds;
        this.clipRetentionDays = clipRetentionDays;
        this.version += 1;
        this.updatedAt = LocalDateTime.now();
    }
}
