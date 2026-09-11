package com.teachdemo.ecommerce.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

public record ShopAfterSaleCreateRequest(
    @NotBlank String orderNo,
    @NotBlank String type,
    @NotNull BigDecimal amount,
    @NotBlank String reason
) {
}
