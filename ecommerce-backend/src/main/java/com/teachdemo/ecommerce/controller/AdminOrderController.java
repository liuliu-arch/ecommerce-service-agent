package com.teachdemo.ecommerce.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.teachdemo.ecommerce.dto.AdminOrderResponse;
import com.teachdemo.ecommerce.dto.AdminOrderUpdateRequest;
import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.service.AdminOrderService;
import com.teachdemo.ecommerce.service.BusinessException;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/orders")
public class AdminOrderController {

    private static final Set<String> ALLOWED_UPDATE_FIELDS = Set.of(
        "orderStatus", "fulfillmentStatus", "logisticsNo", "remark"
    );

    private final AdminOrderService adminOrderService;
    private final ObjectMapper objectMapper;

    public AdminOrderController(AdminOrderService adminOrderService, ObjectMapper objectMapper) {
        this.adminOrderService = adminOrderService;
        this.objectMapper = objectMapper;
    }

    @GetMapping
    public ApiResponse<List<AdminOrderResponse>> list(
        @RequestParam(value = "orderNo", required = false) String orderNo,
        @RequestParam(value = "userId", required = false) String userId,
        @RequestParam(value = "orderStatus", required = false) String orderStatus,
        @RequestParam(value = "paymentStatus", required = false) String paymentStatus,
        @RequestParam(value = "fulfillmentStatus", required = false) String fulfillmentStatus) {
        return ApiResponse.success(adminOrderService.list(orderNo, userId, orderStatus, paymentStatus, fulfillmentStatus));
    }

    @GetMapping("/{orderNo}")
    public ApiResponse<AdminOrderResponse> get(@PathVariable String orderNo) {
        return ApiResponse.success(adminOrderService.get(orderNo));
    }

    @PatchMapping("/{orderNo}")
    public ApiResponse<AdminOrderResponse> update(@PathVariable String orderNo, @RequestBody JsonNode payload) {
        assertAllowedFields(payload);
        AdminOrderUpdateRequest request = objectMapper.convertValue(payload, AdminOrderUpdateRequest.class);
        return ApiResponse.success(adminOrderService.update(orderNo, request));
    }

    private void assertAllowedFields(JsonNode payload) {
        Iterator<String> fieldNames = payload.fieldNames();
        while (fieldNames.hasNext()) {
            String field = fieldNames.next();
            if (!ALLOWED_UPDATE_FIELDS.contains(field)) {
                throw BusinessException.badRequest("ORDER_UPDATE_FIELD_NOT_ALLOWED", "后台订单修改不允许字段：" + field);
            }
        }
    }
}
