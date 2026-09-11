package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.AdminPromotionRequest;
import com.teachdemo.ecommerce.dto.AdminPromotionResponse;
import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.service.AdminPromotionService;
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
@RequestMapping("/api/admin/promotions")
public class AdminPromotionController {

    private final AdminPromotionService adminPromotionService;

    public AdminPromotionController(AdminPromotionService adminPromotionService) {
        this.adminPromotionService = adminPromotionService;
    }

    @GetMapping
    public ApiResponse<List<AdminPromotionResponse>> list(
        @RequestParam(value = "keyword", required = false) String keyword) {
        return ApiResponse.success(adminPromotionService.list(keyword));
    }

    @GetMapping("/{promotionName}")
    public ApiResponse<AdminPromotionResponse> get(@PathVariable String promotionName) {
        return ApiResponse.success(adminPromotionService.get(promotionName));
    }

    @PostMapping
    public ApiResponse<AdminPromotionResponse> create(@RequestBody AdminPromotionRequest request) {
        return ApiResponse.success(adminPromotionService.create(request));
    }

    @PatchMapping("/{promotionName}")
    public ApiResponse<AdminPromotionResponse> update(@PathVariable String promotionName,
                                                      @RequestBody AdminPromotionRequest request) {
        return ApiResponse.success(adminPromotionService.update(promotionName, request));
    }
}
