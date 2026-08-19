package com.insightpilot.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightpilot.dto.ApiDtos.ApproveRequest;
import com.insightpilot.dto.ApiDtos.DlqItem;
import com.insightpilot.dto.ApiDtos.TaskResponse;
import com.insightpilot.entity.Task;
import com.insightpilot.producer.TaskProducer;
import com.insightpilot.repository.AuditLogRepository;
import com.insightpilot.repository.ChatSessionRepository;
import com.insightpilot.repository.MessageRepository;
import com.insightpilot.repository.TaskRepository;
import com.insightpilot.repository.ToolCallLogRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.RecordId;
import org.springframework.data.redis.core.StreamOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class TaskServiceTest {

    private TaskRepository taskRepository;
    private TaskProducer taskProducer;
    private AuditService auditService;
    private StringRedisTemplate redisTemplate;
    private TaskService taskService;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        taskRepository = mock(TaskRepository.class);
        taskProducer = mock(TaskProducer.class);
        auditService = new AuditService(mock(AuditLogRepository.class));
        redisTemplate = mock(StringRedisTemplate.class);

        taskService = new TaskService(
                taskRepository,
                mock(MessageRepository.class),
                mock(ToolCallLogRepository.class),
                mock(ChatSessionRepository.class),
                taskProducer,
                auditService,
                new ObjectMapper(),
                redisTemplate);
        ReflectionTestUtils.setField(taskService, "dlqStream", "task:dlq");
    }

    private Task taskOf(long userId, String status) {
        Task task = new Task();
        task.setTaskId("task-abc");
        task.setUserId(userId);
        task.setStatus(status);
        task.setOutput("{\"answer\":\"ok\"}");
        return task;
    }

    @Test
    void getRejectsForeignTask() {
        when(taskRepository.findByTaskId("task-abc")).thenReturn(Optional.of(taskOf(2L, "done")));
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> taskService.get(1L, "task-abc"));
        assertEquals(HttpStatus.FORBIDDEN, ex.getStatusCode());
    }

    @Test
    void getReturnsNotFoundForMissingTask() {
        when(taskRepository.findByTaskId("missing")).thenReturn(Optional.empty());
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> taskService.get(1L, "missing"));
        assertEquals(HttpStatus.NOT_FOUND, ex.getStatusCode());
    }

    @Test
    void getReturnsOwnedTask() {
        when(taskRepository.findByTaskId("task-abc")).thenReturn(Optional.of(taskOf(1L, "done")));
        TaskResponse response = taskService.get(1L, "task-abc");
        assertEquals("task-abc", response.taskId());
        assertEquals("done", response.status());
    }

    @Test
    void approveRejectsForeignTask() {
        when(taskRepository.findByTaskId("task-abc")).thenReturn(Optional.of(taskOf(2L, "waiting_approval")));
        ResponseStatusException ex = assertThrows(
                ResponseStatusException.class,
                () -> taskService.approve(1L, "task-abc", new ApproveRequest(true, "")));
        assertEquals(HttpStatus.FORBIDDEN, ex.getStatusCode());
    }

    @Test
    void traceRejectsForeignTask() {
        when(taskRepository.findByTaskId("task-abc")).thenReturn(Optional.of(taskOf(2L, "done")));
        assertThrows(ResponseStatusException.class, () -> taskService.trace(1L, "task-abc"));
    }

    @Test
    @SuppressWarnings("unchecked")
    void dlqParsesRedisEntries() {
        StreamOperations<String, Object, Object> ops = mock(StreamOperations.class);
        when(redisTemplate.opsForStream()).thenReturn(ops);

        MapRecord<String, Object, Object> record = mock(MapRecord.class);
        when(record.getId()).thenReturn(RecordId.of("1690000000000-0"));
        when(record.getValue()).thenReturn(Map.of(
                "taskId", "t1",
                "error", "boom",
                "ts", "2026-08-18T00:00:00Z"));

        when(ops.reverseRange(eq("task:dlq"), any(), any())).thenReturn(List.of(record));

        List<DlqItem> items = taskService.dlq();
        assertEquals(1, items.size());
        assertEquals("t1", items.get(0).taskId());
        assertEquals("boom", items.get(0).error());
        assertEquals("2026-08-18T00:00:00Z", items.get(0).ts());
    }

    @Test
    @SuppressWarnings("unchecked")
    void dlqReturnsEmptyWhenNoEntries() {
        StreamOperations<String, Object, Object> ops = mock(StreamOperations.class);
        when(redisTemplate.opsForStream()).thenReturn(ops);
        when(ops.reverseRange(eq("task:dlq"), any(), any())).thenReturn(null);
        assertEquals(0, taskService.dlq().size());
    }
}
