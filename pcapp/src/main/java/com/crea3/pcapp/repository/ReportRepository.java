package com.crea3.pcapp.repository;

import com.crea3.pcapp.entity.ReportEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface ReportRepository extends JpaRepository<ReportEntity, Long> {

    List<ReportEntity> findTop100ByOrderByReceivedAtDesc();

    Optional<ReportEntity> findTop1ByOrderByReceivedAtDesc();
}
