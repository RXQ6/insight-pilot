package com.insightpilot.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

@Entity
@Table(name = "tool_call_logs")
@Getter
@Setter
@NoArgsConstructor
public class ToolCallLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "task_id", length = 64)
    private String taskId;

    @Column(name = "tool_name", length = 64)
    private String toolName;

    @Column(columnDefinition = "text")
    private String input;

    @Column(columnDefinition = "text")
    private String output;

    @Column(length = 16)
    private String status;

    @Column(name = "latency_ms")
    private long latencyMs;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
}
