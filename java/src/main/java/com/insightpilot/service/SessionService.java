package com.insightpilot.service;

import com.insightpilot.dto.ApiDtos.MessageResponse;
import com.insightpilot.dto.ApiDtos.SessionResponse;
import com.insightpilot.entity.ChatSession;
import com.insightpilot.entity.Message;
import com.insightpilot.repository.ChatSessionRepository;
import com.insightpilot.repository.MessageRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;

@Service
@RequiredArgsConstructor
public class SessionService {

    private final ChatSessionRepository sessionRepository;
    private final MessageRepository messageRepository;

    public SessionResponse create(Long userId, String title) {
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle(title);
        session.setCreatedAt(Instant.now());
        session.setUpdatedAt(Instant.now());
        sessionRepository.save(session);
        return new SessionResponse(session.getId(), session.getTitle(), 0, session.getUpdatedAt());
    }

    public List<SessionResponse> list(Long userId) {
        return sessionRepository.findByUserIdOrderByUpdatedAtDesc(userId).stream()
                .map(session -> new SessionResponse(
                        session.getId(),
                        session.getTitle(),
                        messageRepository.countBySessionId(session.getId()),
                        session.getUpdatedAt()))
                .toList();
    }

    public List<MessageResponse> messages(Long userId, Long sessionId) {
        ChatSession session = ownedSession(userId, sessionId);
        return messageRepository.findBySessionIdOrderByCreatedAtAsc(session.getId()).stream()
                .map(message -> new MessageResponse(
                        message.getRole(),
                        message.getContent(),
                        message.getTaskId(),
                        message.getCreatedAt()))
                .toList();
    }

    public void delete(Long userId, Long sessionId) {
        ChatSession session = ownedSession(userId, sessionId);
        messageRepository.deleteBySessionId(session.getId());
        sessionRepository.delete(session);
    }

    private ChatSession ownedSession(Long userId, Long sessionId) {
        ChatSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "session not found"));
        if (!session.getUserId().equals(userId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "forbidden");
        }
        return session;
    }
}
