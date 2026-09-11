package com.teachdemo.ecommerce.security;

import com.teachdemo.ecommerce.service.BusinessException;
import java.util.Objects;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
public class RequestIdentityResolver {

    public String currentUserId(Authentication authentication, String delegatedUserId) {
        if (authentication == null || !authentication.isAuthenticated()) {
            throw BusinessException.forbidden("ORDER_ACCESS_DENIED", "当前调用没有可信用户身份");
        }
        if (authentication.getPrincipal() instanceof AccountPrincipal principal) {
            return principal.getUserId();
        }
        boolean agentService = authentication.getAuthorities().stream()
            .anyMatch(authority -> AgentServiceAuthenticationFilter.SERVICE_ROLE.equals(authority.getAuthority()));
        if (agentService && StringUtils.hasText(delegatedUserId)) {
            return delegatedUserId.trim();
        }
        throw BusinessException.forbidden("ORDER_ACCESS_DENIED", "Agent 服务调用缺少可信的当前用户身份");
    }

    public String requireCurrentUser(Authentication authentication, String delegatedUserId, String requestedUserId) {
        String currentUserId = currentUserId(authentication, delegatedUserId);
        if (!Objects.equals(currentUserId, requestedUserId)) {
            throw BusinessException.forbidden("USER_ACCESS_DENIED", "只能访问当前用户自己的资料和权益");
        }
        return currentUserId;
    }
}
