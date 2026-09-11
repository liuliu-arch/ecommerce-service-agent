package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.CurrentAccountResponse;
import com.teachdemo.ecommerce.entity.UserProfile;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import com.teachdemo.ecommerce.security.AccountPrincipal;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    private final UserProfileRepository userProfileRepository;

    public AuthService(UserProfileRepository userProfileRepository) {
        this.userProfileRepository = userProfileRepository;
    }

    public CurrentAccountResponse toResponse(AccountPrincipal principal) {
        if ("ADMIN".equals(principal.getRole())) {
            return new CurrentAccountResponse(principal.getAccountId(), principal.getUsername(), principal.getRole(),
                null, "管理员", null, null, "/admin");
        }
        UserProfile profile = userProfileRepository.findByUserId(principal.getUserId())
            .orElseThrow(() -> new IllegalArgumentException("User not found: " + principal.getUserId()));
        return new CurrentAccountResponse(principal.getAccountId(), principal.getUsername(), principal.getRole(),
            profile.getUserId(), profile.getNickname(), profile.getMobile(), profile.getMemberLevel(), "/");
    }
}
