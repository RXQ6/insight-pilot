package com.insightpilot.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.insightpilot.entity.Task;
import com.insightpilot.entity.ToolCallLog;
import com.insightpilot.repository.TaskRepository;
import com.insightpilot.repository.ToolCallLogRepository;
import com.insightpilot.service.SseService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.connection.stream.Consumer;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.ReadOffset;
import org.springframework.data.redis.connection.stream.StreamOffset;
import org.springframework.data.redis.connection.stream.StreamReadOptions;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;

@Component
@RequiredArgsConstructor
@Slf4j
public class ResultConsumer implements ApplicationRunner {

    private final StringRedisTemplate redisTemplate;
    private final TaskRepository taskRepository;
    private final ToolCallLogRepository toolCallLogRepository;
    private final SseService sseService;
    private final ObjectMapper objectMapper;

    @Value("${app.redis.task-result-stream:task:result}")
    private String resultStream;

    @Value("${app.redis.result-group:java-control-plane}")
    private String group;

    @Override
    public void run(ApplicationArguments args) {
        Thread thread = new Thread(this::consumeLoop, "result-consumer");
        thread.setDaemon(true);
        thread.start();
    }

    private void consumeLoop() {
        try {
            redisTemplate.opsForStream().createGroup(resultStream, ReadOffset.from("0"), group);
        } catch (Exception e) {
            log.debug("stream group already exists: {}", e.getMessage());
        }
        while (true) {
            try {
                List<MapRecord<String, Object, Object>> records = redisTemplate.opsForStream().read(
                        Consumer.from(group, "java-1"),
                        StreamReadOptions.empty().count(20).block(Duration.ofSeconds(5)),
                        StreamOffset.create(resultStream, ReadOffset.lastConsumed())
                );
                if (records == null) {
                    continue;
                }
                for (MapRecord<String, Object, Object> record : records) {
                    handle(record);
                    redisTemplate.opsForStream().acknowledge(resultStream, group, record.getId());
                }
            } catch (Exception e) {
                log.error("result consumer loop error", e);
                try {
                    Thread.sleep(1000);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }

    private void handle(MapRecord<String, Object, Object> record) {
        Map<Object, Object> value = record.getValue();
        String taskId = value.get("taskId") == null ? null : String.valueOf(value.get("taskId"));
        String type = value.get("type") == null ? null : String.valueOf(value.get("type"));
        String content = value.get("content") == null ? null : String.valueOf(value.get("content"));
        Task task = taskId == null ? null : taskRepository.findByTaskId(taskId).orElse(null);

        switch (type == null ? "" : type) {
            case "status" -> {
                if (task != null) {
                    task.setStatus(parseString(content, "running"));
                    task.setUpdatedAt(Instant.now());
                    taskRepository.save(task);
                }
            }
            case "tool_call" -> saveToolCall(taskId, content);
            case "result" -> {
                if (task != null) {
                    task.setStatus("done");
                    task.setOutput(content);
                    task.setUpdatedAt(Instant.now());
                    taskRepository.save(task);
                }
            }
            case "approval_required" -> {
                if (task != null) {
                    task.setStatus("waiting_approval");
                    task.setUpdatedAt(Instant.now());
                    taskRepository.save(task);
                }
            }
            case "done" -> {
                if (task != null) {
                    task.setStatus("done");
                    try {
                        JsonNode node = objectMapper.readTree(content);
                        task.setLatencyMs(node.path("latencyMs").asLong(0));
                        task.setTokenIn(node.path("tokenIn").asLong(0));
                        task.setTokenOut(node.path("tokenOut").asLong(0));
                        task.setCostCny(node.path("costCny").asDouble(0));
                    } catch (Exception ignored) {
                        // metrics are optional
                    }
                    task.setUpdatedAt(Instant.now());
                    taskRepository.save(task);
                }
            }
            case "error" -> {
                if (task != null) {
                    task.setStatus("error");
                    task.setError(content);
                    task.setUpdatedAt(Instant.now());
                    taskRepository.save(task);
                }
            }
            default -> {
                // ignore unknown event types
            }
        }
        sseService.send(taskId, type, content);
    }

    private void saveToolCall(String taskId, String content) {
        try {
            JsonNode node = objectMapper.readTree(content);
            ToolCallLog toolCallLog = new ToolCallLog();
            toolCallLog.setTaskId(taskId);
            toolCallLog.setToolName(node.path("name").asText("unknown"));
            toolCallLog.setInput(node.path("arguments").toString());
            toolCallLog.setOutput(node.path("output").asText(null));
            toolCallLog.setStatus(node.path("status").asText("success"));
            toolCallLog.setLatencyMs(0);
            toolCallLog.setCreatedAt(Instant.now());
            toolCallLogRepository.save(toolCallLog);
        } catch (Exception e) {
            log.warn("failed to persist tool call: {}", e.getMessage());
        }
    }

    private String parseString(String content, String fallback) {
        if (content == null || content.isBlank()) {
            return fallback;
        }
        try {
            return objectMapper.readValue(content, String.class);
        } catch (Exception e) {
            return content;
        }
    }
}
