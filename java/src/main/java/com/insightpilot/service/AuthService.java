package com.insightpilot.service;

import com.insightpilot.dto.ApiDtos.AuthResponse;
import com.insightpilot.dto.ApiDtos.LoginRequest;
import com.insightpilot.dto.ApiDtos.RegisterRequest;
import com.insightpilot.dto.ApiDtos.UserResponse;
import com.insightpilot.entity.User;
import com.insightpilot.repository.UserRepository;
import com.insightpilot.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;
    private final AuditService auditService;

    public UserResponse register(RegisterRequest request) {
        userRepository.findByUsername(request.username()).ifPresent(user -> {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "username already exists");
        });
        User user = new User();
        user.setUsername(request.username());
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setRole("user");
        userRepository.save(user);
        auditService.record(user.getId(), "register", null, null);
        return toResponse(user);
    }

    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.username())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "bad credentials"));
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "bad credentials");
        }
        auditService.record(user.getId(), "login", null, null);
        String token = jwtUtil.generate(user.getUsername(), user.getRole());
        return new AuthResponse(token, jwtUtil.expireSeconds(), toResponse(user));
    }

    public UserResponse me(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user not found"));
        return toResponse(user);
    }

    public Long userId(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user not found"))
                .getId();
    }

    private UserResponse toResponse(User user) {
        return new UserResponse(user.getId(), user.getUsername(), user.getRole());
    }
}
