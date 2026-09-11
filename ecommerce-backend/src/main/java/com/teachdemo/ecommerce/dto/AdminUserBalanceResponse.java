package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.util.List;

public class AdminUserBalanceResponse {

    private final String userId;
    private final String nickname;
    private final String mobile;
    private final String memberLevel;
    private final String riskLevel;
    private final BigDecimal availableBalance;
    private final List<BalanceTransactionResponse> recentTransactions;

    public AdminUserBalanceResponse(String userId, String nickname, String mobile, String memberLevel,
                                    String riskLevel, BigDecimal availableBalance,
                                    List<BalanceTransactionResponse> recentTransactions) {
        this.userId = userId;
        this.nickname = nickname;
        this.mobile = mobile;
        this.memberLevel = memberLevel;
        this.riskLevel = riskLevel;
        this.availableBalance = availableBalance;
        this.recentTransactions = recentTransactions;
    }

    public String getUserId() { return userId; }
    public String getNickname() { return nickname; }
    public String getMobile() { return mobile; }
    public String getMemberLevel() { return memberLevel; }
    public String getRiskLevel() { return riskLevel; }
    public BigDecimal getAvailableBalance() { return availableBalance; }
    public List<BalanceTransactionResponse> getRecentTransactions() { return recentTransactions; }
}
