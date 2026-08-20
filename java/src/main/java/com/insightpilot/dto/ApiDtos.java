package com.insightpilot.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public final class ApiDtos {

    private ApiDtos() {
    }

    public record RegisterRequest(
            @NotBlank @Size(min = 3, max = 32) String username,
            @NotBlank @Size(min = 8, max = 64) String password) {
    }

    public record LoginRequest(@NotBlank String username, @NotBlank String password) {
    }

    public record UserResponse(Long id, String username, String role) {
    }

    public record AuthResponse(String token, long expiresIn, UserResponse user) {
    }

    public record CreateSessionRequest(@NotBlank String title) {
    }

    public record SessionResponse(Long sessionId, String title, long messageCount, Instant updatedAt) {
    }

    public record MessageResponse(String role, String content, String taskId, Instant createdAt) {
    }

    public record CreateTaskRequest(
            @NotNull Long sessionId,
            @NotBlank String message,
            Map<String, Object> context) {
    }

    public record TaskResponse(String taskId, String status, Object output, String model,
                               long tokenIn, long tokenOut, double costCny, long latencyMs,
                               Instant createdAt, Instant updatedAt) {
    }

    public record TaskListItem(String taskId, String status, Instant createdAt) {
    }

    public record ApproveRequest(boolean approved, String note) {
    }

    public record FeedbackRequest(boolean helpful, String comment) {
    }

    public record ToolTraceItem(String tool, String status, String summary, long latencyMs) {
    }

    public record TraceResponse(String taskId, List<ToolTraceItem> steps) {
    }

    public record DlqItem(String id, String taskId, String error, String ts) {
    }

    public record EvalSummary(String runId, long total, long passed, double sqlAccuracy,
                              double avgCostCny, Instant finishedAt) {
    }

    public record DatasetResponse(Long id, String name, String tableName, long rowCount, Instant createdAt) {
    }

    public record PreviewResponse(List<String> columns, List<Map<String, Object>> rows) {
    }
}