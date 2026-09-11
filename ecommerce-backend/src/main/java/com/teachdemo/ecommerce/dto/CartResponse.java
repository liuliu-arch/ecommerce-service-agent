package com.teachdemo.ecommerce.dto;

import java.math.BigDecimal;
import java.util.List;

public record CartResponse(
    List<CartItemResponse> items,
    BigDecimal selectedTotalAmount,
    Integer selectedItemCount
) {
}
