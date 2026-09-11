package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.LogisticsResponse;
import com.teachdemo.ecommerce.dto.OrderResponse;
import com.teachdemo.ecommerce.security.AgentServiceAuthenticationFilter;
import com.teachdemo.ecommerce.security.RequestIdentityResolver;
import com.teachdemo.ecommerce.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.security.core.Authentication;

@Tag(name = "Orders", description = "查询电商公司订单与物流事实，供客服 Agent 使用")
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;
    private final RequestIdentityResolver requestIdentityResolver;

    public OrderController(OrderService orderService, RequestIdentityResolver requestIdentityResolver) {
        this.orderService = orderService;
        this.requestIdentityResolver = requestIdentityResolver;
    }

    @GetMapping("/{orderNo}")
    @Operation(summary = "Get order details", description = "Query status, payment state, and line items by order number")
    public ApiResponse<OrderResponse> getOrder(
        @Parameter(description = "Order number", example = "SO20260420103000001-a1000001")
        @PathVariable String orderNo,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(orderService.getOrder(orderNo, currentUserId));
    }

    @GetMapping("/{orderNo}/logistics")
    @Operation(summary = "Get logistics details", description = "Query tracking status and logistics events by order number")
    public ApiResponse<LogisticsResponse> getLogistics(
        @Parameter(description = "Order number", example = "SO20260420103000001-a1000001")
        @PathVariable String orderNo,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(orderService.getLogistics(orderNo, currentUserId));
    }
}
