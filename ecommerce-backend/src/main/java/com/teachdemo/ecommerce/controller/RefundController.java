package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.RefundRequestCreateRequest;
import com.teachdemo.ecommerce.dto.RefundRequestResponse;
import com.teachdemo.ecommerce.security.AgentServiceAuthenticationFilter;
import com.teachdemo.ecommerce.security.RequestIdentityResolver;
import com.teachdemo.ecommerce.service.RefundRequestService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Refund", description = "电商公司课程项目中的退款申请模拟接口，用于 Agent 风险控制流程")
@RestController
@RequestMapping("/api/refund/requests")
public class RefundController {

    private final RefundRequestService refundRequestService;
    private final RequestIdentityResolver requestIdentityResolver;

    public RefundController(RefundRequestService refundRequestService,
                            RequestIdentityResolver requestIdentityResolver) {
        this.refundRequestService = refundRequestService;
        this.requestIdentityResolver = requestIdentityResolver;
    }

    @GetMapping("/{requestId}")
    @Operation(summary = "Get refund request")
    public ApiResponse<RefundRequestResponse> getRequest(
        @PathVariable String requestId,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(refundRequestService.getByRequestId(requestId, currentUserId));
    }

    @PostMapping
    @Operation(summary = "Create refund request")
    public ApiResponse<RefundRequestResponse> createRequest(
        @RequestBody RefundRequestCreateRequest request,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(refundRequestService.create(request, currentUserId));
    }
}
