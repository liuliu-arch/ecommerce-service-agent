package com.teachdemo.ecommerce.dto;

public class AdminOrderUpdateRequest {

    private String orderStatus;
    private String fulfillmentStatus;
    private String logisticsNo;
    private String remark;

    public String getOrderStatus() {
        return orderStatus;
    }

    public String getFulfillmentStatus() {
        return fulfillmentStatus;
    }

    public String getLogisticsNo() {
        return logisticsNo;
    }

    public String getRemark() {
        return remark;
    }
}
