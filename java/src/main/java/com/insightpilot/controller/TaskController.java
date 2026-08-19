package com.insightpilot.controller;

import com.insightpilot.dto.ApiDtos.ApproveRequest;
import com.insightpilot.dto.ApiDtos.CreateTaskRequest;
import com.insightpilot.dto.ApiDtos.DlqItem;
import com.insightpilot.dto.ApiDtos.TaskListItem;
import com.insightpilot.dto.ApiDtos.TaskResponse;
import com.insightpilot.dto.ApiDtos.TraceResponse;
import com.insightpilot.service.AuthService;
import com.insightpilot.service.SseService;
import com.insightpilot.service.TaskService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/tasks")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;
    private final SseService sseService;
    private final AuthService authService;

    @PostMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public TaskResponse create(Authentication authentication,
                               @Valid @RequestBody CreateTaskRequest request) {
        return taskService.create(authService.userId(authentication.getName()), request);
    }

    @GetMapping
    public Map<String, List<TaskListItem>> list(Authentication authentication) {
        return Map.of("items", taskService.list(authService.userId(authentication.getName())));
    }

    @GetMapping("/{taskId}")
    public TaskResponse get(Authentication authentication, @PathVariable String taskId) {
        return taskService.get(authService.userId(authentication.getName()), taskId);
    }

    @GetMapping("/{taskId}/trace")
    public TraceResponse trace(Authentication authentication, @PathVariable String taskId) {
        return taskService.trace(authService.userId(authentication.getName()), taskId);
    }

    @GetMapping("/dlq")
    public Map<String, List<DlqItem>> dlq() {
        return Map.of("items", taskService.dlq());
    }

    @PostMapping("/{taskId}/approve")
    public TaskResponse approve(Authentication authentication,
                                @PathVariable String taskId,
                                @RequestBody ApproveRequest request) {
        return taskService.approve(authService.userId(authentication.getName()), taskId, request);
    }

    @GetMapping(value = "/{taskId}/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter events(Authentication authentication, @PathVariable String taskId) {
        taskService.requireOwned(authService.userId(authentication.getName()), taskId);
        return sseService.connect(taskId);
    }
}
