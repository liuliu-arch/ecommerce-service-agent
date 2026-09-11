package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.DemoUserCreateRequest;
import com.teachdemo.ecommerce.dto.DemoUserResponse;
import com.teachdemo.ecommerce.dto.UserPreferenceRequest;
import com.teachdemo.ecommerce.dto.UserPreferenceResponse;
import com.teachdemo.ecommerce.dto.UserCouponResponse;
import com.teachdemo.ecommerce.dto.UserProfileResponse;
import com.teachdemo.ecommerce.security.AgentServiceAuthenticationFilter;
import com.teachdemo.ecommerce.security.RequestIdentityResolver;
import com.teachdemo.ecommerce.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;
import org.springframework.security.core.Authentication;

@Tag(name = "Users", description = "查询电商公司客户资料、低风险偏好和优惠券")
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;
    private final RequestIdentityResolver requestIdentityResolver;

    public UserController(UserService userService, RequestIdentityResolver requestIdentityResolver) {
        this.userService = userService;
        this.requestIdentityResolver = requestIdentityResolver;
    }

    @GetMapping("/{userId}")
    @Operation(summary = "Get user profile")
    public ApiResponse<UserProfileResponse> getProfile(
        @PathVariable String userId,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        requestIdentityResolver.requireCurrentUser(authentication, delegatedUserId, userId);
        return ApiResponse.success(userService.getProfile(userId));
    }

    @GetMapping("/{userId}/preferences")
    @Operation(summary = "Get user preferences")
    public ApiResponse<UserPreferenceResponse> getPreference(
        @PathVariable String userId,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        requestIdentityResolver.requireCurrentUser(authentication, delegatedUserId, userId);
        return ApiResponse.success(userService.getPreference(userId));
    }

    @GetMapping("/{userId}/coupons")
    @Operation(summary = "List user coupons", description = "Query available coupons for a user, optionally filtered by product category")
    public ApiResponse<List<UserCouponResponse>> listCoupons(
        @PathVariable String userId,
        @RequestParam(value = "productCategory", required = false) String productCategory,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        requestIdentityResolver.requireCurrentUser(authentication, delegatedUserId, userId);
        return ApiResponse.success(userService.listCoupons(userId, productCategory));
    }

    @PostMapping("/{userId}/preferences")
    @Operation(summary = "Save low-risk user preferences")
    public ApiResponse<UserPreferenceResponse> savePreference(
        @PathVariable String userId,
        @RequestBody UserPreferenceRequest request,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        requestIdentityResolver.requireCurrentUser(authentication, delegatedUserId, userId);
        return ApiResponse.success(userService.savePreference(userId, request));
    }

    @PostMapping("/demo")
    @Operation(summary = "Create course project user")
    public ApiResponse<DemoUserResponse> createDemoUser(@RequestBody DemoUserCreateRequest request) {
        return ApiResponse.success(userService.createDemoUser(request));
    }
}
