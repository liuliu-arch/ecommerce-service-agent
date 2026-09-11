package com.teachdemo.ecommerce.dto;

public class AfterSaleRequestCreateRequest {

    private String orderNo;
    private String userId;
    private String requestType;
    private String reason;

    public String getOrderNo() {
        return orderNo;
    }

    public String getUserId() {
        return userId;
    }

    public String getRequestType() {
        return requestType;
    }

    public String getReason() {
        return reason;
    }
}
