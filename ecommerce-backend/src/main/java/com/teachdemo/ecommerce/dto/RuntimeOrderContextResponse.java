package com.teachdemo.ecommerce.dto;

import java.util.List;

/**
 * Runtime Context 订单窗口及其完整性信息。
 */
public record RuntimeOrderContextResponse(
    List<RuntimeOrderSummaryResponse> orders,
    boolean truncated,
    int limit
) {
}
