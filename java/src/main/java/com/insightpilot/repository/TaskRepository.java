package com.insightpilot.repository;

import com.insightpilot.entity.Task;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface TaskRepository extends JpaRepository<Task, Long> {
    Optional<Task> findByTaskId(String taskId);

    List<Task> findByUserIdOrderByCreatedAtDesc(Long userId);
}
