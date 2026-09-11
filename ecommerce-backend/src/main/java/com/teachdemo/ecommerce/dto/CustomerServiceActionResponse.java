package com.teachdemo.ecommerce.dto;

public class CustomerServiceActionResponse {

    private final String code;

    private final String label;

    public CustomerServiceActionResponse(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public String getCode() {
        return code;
    }

    public String getLabel() {
        return label;
    }
}
