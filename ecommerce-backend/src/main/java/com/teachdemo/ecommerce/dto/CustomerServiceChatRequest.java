package com.teachdemo.ecommerce.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

public class CustomerServiceChatRequest {

    @NotBlank
    private String message;

    private String sessionId;

    @Valid
    private CustomerServicePageContextRequest pageContext;

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }

    public CustomerServicePageContextRequest getPageContext() {
        return pageContext;
    }

    public void setPageContext(CustomerServicePageContextRequest pageContext) {
        this.pageContext = pageContext;
    }
}
