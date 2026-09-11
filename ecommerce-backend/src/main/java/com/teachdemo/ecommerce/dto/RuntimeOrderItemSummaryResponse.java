package com.teachdemo.ecommerce.dto;

/**
 * Runtime Context 使用的订单商品安全摘要。
 */
public record RuntimeOrderItemSummaryResponse(
    String productName,
    Integer quantity,
    Boolean returnable
) {
}
