package com.insightpilot.controller;

import com.insightpilot.dto.ApiDtos.CreateSessionRequest;
import com.insightpilot.dto.ApiDtos.MessageResponse;
import com.insightpilot.dto.ApiDtos.SessionResponse;
import com.insightpilot.service.AuthService;
import com.insightpilot.service.SessionService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final SessionService sessionService;
    private final AuthService authService;

    @PostMapping
    public SessionResponse create(Authentication authentication,
                                  @Valid @RequestBody CreateSessionRequest request) {
        return sessionService.create(authService.userId(authentication.getName()), request.title());
    }

    @GetMapping
    public Map<String, List<SessionResponse>> list(Authentication authentication) {
        return Map.of("items", sessionService.list(authService.userId(authentication.getName())));
    }

    @GetMapping("/{id}/messages")
    public Map<String, List<MessageResponse>> messages(Authentication authentication,
                                                       @PathVariable Long id) {
        return Map.of("items",
                sessionService.messages(authService.userId(authentication.getName()), id));
    }

    @DeleteMapping("/{id}")
    public Map<String, Boolean> delete(Authentication authentication, @PathVariable Long id) {
        sessionService.delete(authService.userId(authentication.getName()), id);
        return Map.of("deleted", true);
    }
}
