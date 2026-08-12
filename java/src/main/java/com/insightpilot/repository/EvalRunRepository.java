package com.insightpilot.repository;

import com.insightpilot.entity.EvalRun;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface EvalRunRepository extends JpaRepository<EvalRun, Long> {
    Optional<EvalRun> findTopByOrderByCreatedAtDesc();
}
