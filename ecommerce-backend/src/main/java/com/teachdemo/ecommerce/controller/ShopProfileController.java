package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.UserProfileResponse;
import com.teachdemo.ecommerce.security.AccountPrincipal;
import com.teachdemo.ecommerce.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Shop", description = "用户商城登录态验证接口")
@RestController
@RequestMapping("/api/shop")
public class ShopProfileController {

    private final UserService userService;

    public ShopProfileController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/profile")
    @Operation(summary = "Get current user's profile")
    public ApiResponse<UserProfileResponse> profile(@AuthenticationPrincipal AccountPrincipal principal) {
        // 用户资料归属由登录态决定，不接收 userId 参数，避免前端伪造其他用户身份。
        return ApiResponse.success(userService.getProfile(principal.getUserId()));
    }
}
