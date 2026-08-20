package com.insightpilot.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightpilot.dto.ApiDtos.ApproveRequest;
import com.insightpilot.dto.ApiDtos.CreateTaskRequest;
import com.insightpilot.dto.ApiDtos.DlqItem;
import com.insightpilot.dto.ApiDtos.FeedbackRequest;
import com.insightpilot.dto.ApiDtos.TaskListItem;
import com.insightpilot.dto.ApiDtos.TaskResponse;
import com.insightpilot.dto.ApiDtos.ToolTraceItem;
import com.insightpilot.dto.ApiDtos.TraceResponse;
import com.insightpilot.entity.ChatSession;
import com.insightpilot.entity.Feedback;
import com.insightpilot.entity.Message;
import com.insightpilot.entity.Task;
import com.insightpilot.producer.TaskProducer;
import com.insightpilot.repository.ChatSessionRepository;
import com.insightpilot.repository.FeedbackRepository;
import com.insightpilot.repository.MessageRepository;
import com.insightpilot.repository.TaskRepository;
import com.insightpilot.repository.ToolCallLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.connection.Limit;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TaskService {

    private final TaskRepository taskRepository;
    private final MessageRepository messageRepository;
    private final ToolCallLogRepository toolCallLogRepository;
    private final ChatSessionRepository sessionRepository;
    private final TaskProducer taskProducer;
    private final AuditService auditService;
    private final ObjectMapper objectMapper;
    private final StringRedisTemplate redisTemplate;
    private final FeedbackRepository feedbackRepository;

    @Value("${app.redis.task-dlq-stream:task:dlq}")
    private String dlqStream;

    @Transactional
    public TaskResponse create(Long userId, CreateTaskRequest request) {
        ChatSession session = sessionRepository.findById(request.sessionId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "session not found"));
        if (!session.getUserId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "forbidden");
        }

        Task task = new Task();
        task.setTaskId(UUID.randomUUID().toString().replace("-", ""));
        task.setSessionId(session.getId());
        task.setUserId(userId);
        task.setStatus("pending");
        task.setInput(asJson(Map.of("message", request.message())));
        task.setCreatedAt(Instant.now());
        task.setUpdatedAt(Instant.now());
        taskRepository.save(task);

        Message userMessage = new Message();
        userMessage.setSessionId(session.getId());
        userMessage.setRole("user");
        userMessage.setContent(request.message());
        userMessage.setTaskId(task.getTaskId());
        userMessage.setCreatedAt(Instant.now());
        messageRepository.save(userMessage);

        session.setUpdatedAt(Instant.now());
        sessionRepository.save(session);

        List<Map<String, String>> history = messageRepository
                .findBySessionIdOrderByCreatedAtAsc(session.getId())
                .stream()
                .limit(10)
                .map(message -> Map.of(
                        "role", message.getRole(),
                        "content", message.getContent() == null ? "" : message.getContent()))
                .toList();
        taskProducer.submit(task, request.message(), asJson(history));
        auditService.record(userId, "create_task", task.getTaskId(), null);
        return toResponse(task);
    }

    public TaskResponse get(Long userId, String taskId) {
        return toResponse(requireOwned(userId, taskId));
    }

    public List<TaskListItem> list(Long userId) {
        return taskRepository.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(task -> new TaskListItem(task.getTaskId(), task.getStatus(), task.getCreatedAt()))
                .toList();
    }

    public Task requireOwned(Long userId, String taskId) {
        Task task = taskRepository.findByTaskId(taskId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "task not found"));
        if (userId != null && !task.getUserId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "forbidden");
        }
        return task;
    }

    public TraceResponse trace(Long userId, String taskId) {
        requireOwned(userId, taskId);
        List<ToolTraceItem> steps = toolCallLogRepository.findByTaskIdOrderByCreatedAtAsc(taskId).stream()
                .map(log -> new ToolTraceItem(
                        log.getToolName(),
                        log.getStatus(),
                        log.getOutput(),
                        log.getLatencyMs()))
                .toList();
        return new TraceResponse(taskId, steps);
    }

    /** 查看最近进入死信队列的失败任务，用于运维排查。 */
    public List<DlqItem> dlq() {
        List<MapRecord<String, Object, Object>> records = redisTemplate
                .opsForStream()
                .reverseRange(dlqStream, Range.unbounded(), Limit.limit().count(50));
        if (records == null) {
            return List.of();
        }
        return records.stream().map(record -> {
            Map<Object, Object> value = record.getValue();
            return new DlqItem(
                    record.getId().getValue(),
                    stringValue(value.get("taskId")),
                    stringValue(value.get("error")),
                    stringValue(value.get("ts")));
        }).toList();
    }

    private String stringValue(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    @Transactional
    public TaskResponse approve(Long userId, String taskId, ApproveRequest request) {
        Task task = requireOwned(userId, taskId);
        if (!"waiting_approval".equals(task.getStatus())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "task is not waiting for approval");
        }
        if (!request.approved()) {
            task.setStatus("done");
            task.setError("operation rejected by user");
        } else {
            task.setStatus("running");
        }
        task.setUpdatedAt(Instant.now());
        taskRepository.save(task);
        taskProducer.resume(taskId, request.approved());
        auditService.record(userId, "approve_task", taskId, null);
        return toResponse(task);
    }

    @Transactional
    public Map<String, Object> feedback(Long userId, String taskId, FeedbackRequest request) {
        requireOwned(userId, taskId);
        Feedback feedback = new Feedback();
        feedback.setTaskId(taskId);
        feedback.setUserId(userId);
        feedback.setHelpful(request.helpful());
        feedback.setComment(request.comment());
        feedbackRepository.save(feedback);
        auditService.record(userId, "feedback_task", taskId, request.helpful() ? "helpful" : "not_helpful");
        return Map.of("recorded", true);
    }

    private TaskResponse toResponse(Task task) {
        Object output = null;
        if (task.getOutput() != null) {
            try {
                output = objectMapper.readValue(task.getOutput(), Object.class);
            } catch (JsonProcessingException e) {
                output = task.getOutput();
            }
        }
        return new TaskResponse(
                task.getTaskId(),
                task.getStatus(),
                output,
                task.getModel(),
                task.getTokenIn(),
                task.getTokenOut(),
                task.getCostCny(),
                task.getLatencyMs(),
                task.getCreatedAt(),
                task.getUpdatedAt());
    }

    private String asJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("failed to serialize json", e);
        }
    }
}
