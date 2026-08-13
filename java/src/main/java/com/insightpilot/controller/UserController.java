package com.insightpilot.controller;

import com.insightpilot.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @GetMapping("/demo")
    public Map<String, Boolean> demo(Authentication authentication) {
        return Map.of("enabled", userService.demoEnabled(authentication.getName()));
    }

    @PostMapping("/demo")
    public Map<String, Boolean> setDemo(Authentication authentication,
                                        @RequestBody Map<String, Boolean> body) {
        boolean enabled = Boolean.TRUE.equals(body.get("enabled"));
        return Map.of("enabled", userService.setDemoEnabled(authentication.getName(), enabled));
    }
}