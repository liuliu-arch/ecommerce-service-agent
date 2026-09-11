package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;

@Schema(description = "Order line item")
public class OrderItemResponse {

    @Schema(description = "Product ID", example = "1")
    private final Long productId;
    @Schema(description = "Product name", example = "Noise Cancelling Headphones")
    private final String productName;
    @Schema(description = "Quantity", example = "1")
    private final Integer quantity;
    @Schema(description = "Unit price", example = "299.00")
    private final BigDecimal unitPrice;

    public OrderItemResponse(Long productId, String productName, Integer quantity, BigDecimal unitPrice) {
        this.productId = productId;
        this.productName = productName;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
    }

    public Long getProductId() {
        return productId;
    }

    public String getProductName() {
        return productName;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }
}
