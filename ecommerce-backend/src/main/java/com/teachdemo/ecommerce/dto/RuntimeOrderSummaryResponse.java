package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 课程调试后台可注入 Agent Runtime Context 的订单安全摘要。
 *
 * <p>这里只提供订单澄清需要的字段，不返回地址、手机号、支付凭据等敏感信息。</p>
 */
public record RuntimeOrderSummaryResponse(
    String orderNo,
    String status,
    String paymentStatus,
    String fulfillmentStatus,
    BigDecimal totalAmount,
    LocalDateTime createdAt,
    LocalDateTime paidAt,
    LocalDateTime shippedAt,
    LocalDateTime deliveredAt,
    String logisticsNo,
    List<String> itemSummary,
    List<RuntimeOrderItemSummaryResponse> items,
    Boolean returnable
) {
}
