package com.insightpilot.repository;

import com.insightpilot.entity.Dataset;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface DatasetRepository extends JpaRepository<Dataset, Long> {
    List<Dataset> findByUserIdOrderByCreatedAtDesc(Long userId);
}