package com.insightpilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

@Entity
@Table(name = "eval_runs")
@Getter
@Setter
@NoArgsConstructor
public class EvalRun {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "run_id", length = 64)
    private String runId;

    @Column(name = "case_id")
    private Long caseId;

    @Column(name = "task_id", length = 64)
    private String taskId;

    @Column
    private boolean pass;

    @Column
    private double score;

    @Column(name = "latency_ms")
    private long latencyMs;

    @Column(name = "cost_cny")
    private double costCny;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @PrePersist
    void prePersist() {
        createdAt = Instant.now();
    }
}
