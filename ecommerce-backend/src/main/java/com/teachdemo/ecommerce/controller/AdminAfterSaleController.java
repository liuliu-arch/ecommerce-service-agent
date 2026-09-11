package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.AdminAfterSaleResponse;
import com.teachdemo.ecommerce.dto.AdminAfterSaleReviewRequest;
import com.teachdemo.ecommerce.dto.AdminAfterSaleReviewResponse;
import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.security.AccountPrincipal;
import com.teachdemo.ecommerce.service.AdminAfterSaleService;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/after-sales")
public class AdminAfterSaleController {

    private final AdminAfterSaleService adminAfterSaleService;

    public AdminAfterSaleController(AdminAfterSaleService adminAfterSaleService) {
        this.adminAfterSaleService = adminAfterSaleService;
    }

    @GetMapping
    public ApiResponse<List<AdminAfterSaleResponse>> list(
        @RequestParam(value = "requestNo", required = false) String requestNo,
        @RequestParam(value = "orderNo", required = false) String orderNo,
        @RequestParam(value = "userId", required = false) String userId,
        @RequestParam(value = "type", required = false) String type,
        @RequestParam(value = "status", required = false) String status) {
        return ApiResponse.success(adminAfterSaleService.list(requestNo, orderNo, userId, type, status));
    }

    @GetMapping("/{requestNo}")
    public ApiResponse<AdminAfterSaleResponse> get(@PathVariable String requestNo) {
        return ApiResponse.success(adminAfterSaleService.get(requestNo));
    }

    @PostMapping("/{requestNo}/approve")
    public ApiResponse<AdminAfterSaleReviewResponse> approve(
        @PathVariable String requestNo,
        @RequestBody AdminAfterSaleReviewRequest request,
        @AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(adminAfterSaleService.approve(requestNo, request, principal.getUsername()));
    }

    @PostMapping("/{requestNo}/reject")
    public ApiResponse<AdminAfterSaleReviewResponse> reject(
        @PathVariable String requestNo,
        @RequestBody AdminAfterSaleReviewRequest request,
        @AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(adminAfterSaleService.reject(requestNo, request, principal.getUsername()));
    }

    @PostMapping("/{requestNo}/need-more-info")
    public ApiResponse<AdminAfterSaleReviewResponse> needMoreInfo(
        @PathVariable String requestNo,
        @RequestBody AdminAfterSaleReviewRequest request,
        @AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(adminAfterSaleService.needMoreInfo(requestNo, request, principal.getUsername()));
    }
}
