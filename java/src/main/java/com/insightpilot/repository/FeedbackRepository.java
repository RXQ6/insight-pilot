package com.insightpilot.repository;

import com.insightpilot.entity.Feedback;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface FeedbackRepository extends JpaRepository<Feedback, Long> {

    List<Feedback> findByTaskId(String taskId);

    long countByHelpful(boolean helpful);
}
