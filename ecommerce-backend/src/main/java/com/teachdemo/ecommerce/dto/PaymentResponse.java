package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record PaymentResponse(
    String orderNo,
    String orderStatus,
    String paymentStatus,
    BigDecimal paidAmount,
    BigDecimal balanceBefore,
    BigDecimal balanceAfter,
    String transactionNo,
    LocalDateTime paidAt
) {
}
