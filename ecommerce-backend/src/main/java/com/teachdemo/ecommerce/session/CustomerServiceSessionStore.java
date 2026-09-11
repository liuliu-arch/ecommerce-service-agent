package com.teachdemo.ecommerce.session;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import org.springframework.stereotype.Component;

@Component
public class CustomerServiceSessionStore {

    private final ConcurrentMap<String, CustomerServiceSession> sessions = new ConcurrentHashMap<>();

    public CustomerServiceSession getOrCreate(String sessionId, String userId) {
        return sessions.compute(sessionId, (key, existing) -> {
            if (existing == null) {
                return new CustomerServiceSession(sessionId, userId);
            }
            existing.touch();
            return existing;
        });
    }

    public Optional<CustomerServiceSession> find(String sessionId) {
        return Optional.ofNullable(sessions.get(sessionId));
    }

    public void save(CustomerServiceSession session) {
        session.touch();
        sessions.put(session.getSessionId(), session);
    }

    public void clear() {
        sessions.clear();
    }

    public void expire(String sessionId) {
        find(sessionId).ifPresent(session -> session.setExpiresAt(LocalDateTime.now().minusSeconds(1)));
    }
}
