package com.insightpilot.repository;

import com.insightpilot.entity.ToolCallLog;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ToolCallLogRepository extends JpaRepository<ToolCallLog, Long> {
    List<ToolCallLog> findByTaskIdOrderByCreatedAtAsc(String taskId);
}
