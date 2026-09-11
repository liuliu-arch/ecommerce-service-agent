package com.teachdemo.ecommerce.dto;

public class UserProfileResponse {

    private final String userId;
    private final String nickname;
    private final String mobile;
    private final String memberLevel;
    private final String riskLevel;

    public UserProfileResponse(String userId, String nickname, String memberLevel, String riskLevel) {
        this(userId, nickname, null, memberLevel, riskLevel);
    }

    public UserProfileResponse(String userId, String nickname, String mobile, String memberLevel, String riskLevel) {
        this.userId = userId;
        this.nickname = nickname;
        this.mobile = mobile;
        this.memberLevel = memberLevel;
        this.riskLevel = riskLevel;
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

    public String getRiskLevel() {
        return riskLevel;
    }
}
