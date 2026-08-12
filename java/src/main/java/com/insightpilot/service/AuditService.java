package com.insightpilot.service;

import com.insightpilot.entity.AuditLog;
import com.insightpilot.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuditService {

    private final AuditLogRepository auditLogRepository;

    public void record(Long userId, String action, String detail, String ip) {
        AuditLog log = new AuditLog();
        log.setUserId(userId);
        log.setAction(action);
        log.setDetail(detail);
        log.setIp(ip);
        auditLogRepository.save(log);
    }
}
