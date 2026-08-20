package com.insightpilot.config;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.Map;

/** 统一错误响应：{code, message, timestamp}，避免默认错误格式泄露内部细节。 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, Object>> handleResponseStatus(ResponseStatusException ex) {
        return ResponseEntity.status(ex.getStatusCode())
                .body(Map.of(
                        "code", ex.getStatusCode().value(),
                        "message", ex.getReason() == null ? ex.getStatusCode().toString() : ex.getReason(),
                        "timestamp", Instant.now().toString()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGeneric(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of(
                        "code", 500,
                        "message", "internal server error",
                        "timestamp", Instant.now().toString()));
    }
}
