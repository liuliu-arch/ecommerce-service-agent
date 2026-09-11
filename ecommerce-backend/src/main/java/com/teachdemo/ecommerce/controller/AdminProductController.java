package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.AdminProductRequest;
import com.teachdemo.ecommerce.dto.AdminProductResponse;
import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.service.AdminProductService;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/admin/products")
public class AdminProductController {

    private final AdminProductService adminProductService;

    public AdminProductController(AdminProductService adminProductService) {
        this.adminProductService = adminProductService;
    }

    @GetMapping
    public ApiResponse<List<AdminProductResponse>> list(
        @RequestParam(value = "keyword", required = false) String keyword,
        @RequestParam(value = "category", required = false) String category,
        @RequestParam(value = "status", required = false) String status) {
        return ApiResponse.success(adminProductService.list(keyword, category, status));
    }

    @PostMapping
    public ApiResponse<AdminProductResponse> create(@RequestBody AdminProductRequest request) {
        return ApiResponse.success(adminProductService.create(request));
    }

    @PatchMapping("/{productId}")
    public ApiResponse<AdminProductResponse> update(@PathVariable Long productId,
                                                    @RequestBody AdminProductRequest request) {
        return ApiResponse.success(adminProductService.update(productId, request));
    }

    @PostMapping("/{productId}/publish")
    public ApiResponse<AdminProductResponse> publish(@PathVariable Long productId) {
        return ApiResponse.success(adminProductService.publish(productId));
    }

    @PostMapping("/{productId}/unpublish")
    public ApiResponse<AdminProductResponse> unpublish(@PathVariable Long productId) {
        return ApiResponse.success(adminProductService.unpublish(productId));
    }
}
