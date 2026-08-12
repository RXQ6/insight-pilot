package com.insightpilot.producer;

import com.insightpilot.entity.Task;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.connection.stream.StreamRecords;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class TaskProducer {

    private final StringRedisTemplate redisTemplate;

    @Value("${app.redis.task-input-stream:task:input}")
    private String inputStream;

    @Value("${app.redis.task-result-stream:task:result}")
    private String resultStream;

    public void submit(Task task, String message, String historyJson) {
        Map<String, String> payload = new HashMap<>();
        payload.put("taskId", task.getTaskId());
        payload.put("sessionId", String.valueOf(task.getSessionId()));
        payload.put("userId", String.valueOf(task.getUserId()));
        payload.put("message", message);
        payload.put("history", historyJson == null ? "" : historyJson);
        payload.put("maxSteps", "8");
        payload.put("costCapCny", "0.2");
        payload.put("createdAt", String.valueOf(System.currentTimeMillis()));
        redisTemplate.opsForStream().add(StreamRecords.string(payload).withStreamKey(inputStream));
    }

    public void publishEvent(String taskId, String type, String content) {
        Map<String, String> payload = new HashMap<>();
        payload.put("taskId", taskId);
        payload.put("type", type);
        payload.put("content", content);
        payload.put("ts", String.valueOf(System.currentTimeMillis()));
        redisTemplate.opsForStream().add(StreamRecords.string(payload).withStreamKey(resultStream));
    }

    public void resume(String taskId, boolean approved) {
        Map<String, String> payload = new HashMap<>();
        payload.put("taskId", taskId);
        payload.put("action", "resume");
        payload.put("approved", String.valueOf(approved));
        redisTemplate.opsForStream().add(StreamRecords.string(payload).withStreamKey(inputStream));
    }
}
