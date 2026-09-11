package com.teachdemo.ecommerce.dto;

public class CurrentAccountResponse {

    private final Long accountId;
    private final String username;
    private final String role;
    private final String userId;
    private final String nickname;
    private final String mobile;
    private final String memberLevel;
    private final String redirectPath;

    public CurrentAccountResponse(Long accountId, String username, String role, String userId, String nickname,
                                  String mobile, String memberLevel, String redirectPath) {
        this.accountId = accountId;
        this.username = username;
        this.role = role;
        this.userId = userId;
        this.nickname = nickname;
        this.mobile = mobile;
        this.memberLevel = memberLevel;
        this.redirectPath = redirectPath;
    }

    public Long getAccountId() {
        return accountId;
    }

    public String getUsername() {
        return username;
    }

    public String getRole() {
        return role;
    }

    public String getUserId() {
        return userId;
    }

    public String getNickname() {
        return nickname;
    }

    public String getMobile() {
        return mobile;
    }

    public String getMemberLevel() {
        return memberLevel;
    }

    public String getRedirectPath() {
        return redirectPath;
    }
}
