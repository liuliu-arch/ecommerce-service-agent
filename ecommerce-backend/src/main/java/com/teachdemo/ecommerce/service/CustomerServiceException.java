package com.teachdemo.ecommerce.service;

import org.springframework.http.HttpStatus;

public class CustomerServiceException extends RuntimeException {

    private final HttpStatus status;

    private final String code;

    public CustomerServiceException(HttpStatus status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public String getCode() {
        return code;
    }
}
