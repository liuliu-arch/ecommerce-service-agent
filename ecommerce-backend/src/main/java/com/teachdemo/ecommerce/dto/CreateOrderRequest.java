package com.teachdemo.ecommerce.dto;

import jakarta.validation.constraints.Min;
import java.util.List;

public record CreateOrderRequest(
    String source,
    List<Long> cartItemIds,
    Long productId,
    @Min(1) Integer quantity,
    String remark
) {
}
