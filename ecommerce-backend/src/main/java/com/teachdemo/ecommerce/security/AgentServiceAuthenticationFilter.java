package com.teachdemo.ecommerce.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
public class AgentServiceAuthenticationFilter extends OncePerRequestFilter {

    public static final String SERVICE_TOKEN_HEADER = "X-Agent-Service-Token";
    public static final String DELEGATED_USER_HEADER = "X-Agent-User-Id";
    public static final String SERVICE_PRINCIPAL = "xiaozhe-agent-service";
    public static final String SERVICE_ROLE = "ROLE_AGENT_SERVICE";

    private final String configuredToken;

    public AgentServiceAuthenticationFilter(
        @Value("${agent.service.auth-token:}") String configuredToken) {
        this.configuredToken = configuredToken;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String presentedToken = request.getHeader(SERVICE_TOKEN_HEADER);
        if (SecurityContextHolder.getContext().getAuthentication() == null
            && tokenMatches(presentedToken)) {
            var authentication = new UsernamePasswordAuthenticationToken(
                SERVICE_PRINCIPAL,
                null,
                List.of(new SimpleGrantedAuthority(SERVICE_ROLE))
            );
            SecurityContextHolder.getContext().setAuthentication(authentication);
        }
        filterChain.doFilter(request, response);
    }

    private boolean tokenMatches(String presentedToken) {
        if (!StringUtils.hasText(configuredToken) || !StringUtils.hasText(presentedToken)) {
            return false;
        }
        return MessageDigest.isEqual(
            configuredToken.getBytes(StandardCharsets.UTF_8),
            presentedToken.getBytes(StandardCharsets.UTF_8)
        );
    }
}
