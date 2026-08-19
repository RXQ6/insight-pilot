package com.insightpilot.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class JwtUtilTest {

    private JwtUtil jwtUtil;

    @BeforeEach
    void setUp() {
        // HS256 要求 secret >= 32 字节
        jwtUtil = new JwtUtil("insight-pilot-test-secret-0123456789-0123456789", 24);
    }

    @Test
    void generateAndValidateRoundTrip() {
        String token = jwtUtil.generate("alice", "user");
        assertTrue(jwtUtil.validate(token));
        assertEquals("alice", jwtUtil.username(token));
        assertEquals("user", jwtUtil.role(token));
    }

    @Test
    void rejectsTamperedToken() {
        String token = jwtUtil.generate("alice", "user");
        String tampered = token.substring(0, token.length() - 4) + "zzzz";
        assertFalse(jwtUtil.validate(tampered));
    }

    @Test
    void rejectsGarbageInput() {
        assertFalse(jwtUtil.validate("not-a-jwt"));
        assertFalse(jwtUtil.validate(""));
    }

    @Test
    void expireSecondsDerivedFromHours() {
        assertEquals(24 * 3600, jwtUtil.expireSeconds());
    }
}
