package com.teachdemo.ecommerce.dto;

public class ApprovalDecisionRequest {

    private String operator;
    private String comment;

    public String getOperator() {
        return operator;
    }

    public void setOperator(String operator) {
        this.operator = operator;
    }

    public String getComment() {
        return comment;
    }
}
