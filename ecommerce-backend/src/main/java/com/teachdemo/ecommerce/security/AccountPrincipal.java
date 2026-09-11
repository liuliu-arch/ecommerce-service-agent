package com.teachdemo.ecommerce.security;

import com.teachdemo.ecommerce.entity.AppAccount;
import java.util.Collection;
import java.util.List;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;

public class AccountPrincipal implements UserDetails {

    private final Long accountId;
    private final String username;
    private final String passwordHash;
    private final String role;
    private final Boolean enabled;
    private final String userId;

    public AccountPrincipal(AppAccount account) {
        this.accountId = account.getId();
        this.username = account.getUsername();
        this.passwordHash = account.getPasswordHash();
        this.role = account.getRole();
        this.enabled = account.getEnabled();
        this.userId = account.getUserId();
    }

    public Long getAccountId() {
        return accountId;
    }

    public String getRole() {
        return role;
    }

    public String getUserId() {
        return userId;
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return List.of(new SimpleGrantedAuthority("ROLE_" + role));
    }

    @Override
    public String getPassword() {
        return passwordHash;
    }

    @Override
    public String getUsername() {
        return username;
    }

    @Override
    public boolean isEnabled() {
        return Boolean.TRUE.equals(enabled);
    }
}
