package com.insightpilot.service;

import com.insightpilot.entity.User;
import com.insightpilot.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    public boolean demoEnabled(String username) {
        return userRepository.findByUsername(username)
                .map(User::isDemoEnabled)
                .orElse(false);
    }

    @Transactional
    public boolean setDemoEnabled(String username, boolean enabled) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "user not found"));
        user.setDemoEnabled(enabled);
        userRepository.save(user);
        return enabled;
    }
}