package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDateTime;

@Entity
@Table(name = "app_account")
public class AppAccount {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String username;

    @Column(nullable = false)
    private String passwordHash;

    @Column(nullable = false)
    private String role;

    @Column(nullable = false)
    private Boolean enabled;

    private String userId;

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    protected AppAccount() {
    }

    public AppAccount(String username, String passwordHash, String role, Boolean enabled, String userId,
                      LocalDateTime createdAt, LocalDateTime updatedAt) {
        this.username = username;
        this.passwordHash = passwordHash;
        this.role = role;
        this.enabled = enabled;
        this.userId = userId;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    public Long getId() {
        return id;
    }

    public String getUsername() {
        return username;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public String getRole() {
        return role;
    }

    public Boolean getEnabled() {
        return enabled;
    }

    public String getUserId() {
        return userId;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void syncDemoCredentials(String passwordHash, String role, Boolean enabled, String userId,
                                    LocalDateTime updatedAt) {
        this.passwordHash = passwordHash;
        this.role = role;
        this.enabled = enabled;
        this.userId = userId;
        this.updatedAt = updatedAt;
    }
}
