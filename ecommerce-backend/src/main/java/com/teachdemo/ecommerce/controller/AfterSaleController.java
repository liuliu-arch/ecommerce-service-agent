package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.AfterSalePolicyResponse;
import com.teachdemo.ecommerce.dto.AfterSaleRequestCreateRequest;
import com.teachdemo.ecommerce.dto.AfterSaleRequestResponse;
import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.security.AgentServiceAuthenticationFilter;
import com.teachdemo.ecommerce.security.RequestIdentityResolver;
import com.teachdemo.ecommerce.service.AfterSaleRequestService;
import com.teachdemo.ecommerce.service.AfterSaleService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "After-sale", description = "Query refund, return, and exchange policy rules")
@RestController
@RequestMapping("/api/after-sale")
public class AfterSaleController {

    private final AfterSaleService afterSaleService;
    private final AfterSaleRequestService afterSaleRequestService;
    private final RequestIdentityResolver requestIdentityResolver;

    public AfterSaleController(AfterSaleService afterSaleService,
                               AfterSaleRequestService afterSaleRequestService,
                               RequestIdentityResolver requestIdentityResolver) {
        this.afterSaleService = afterSaleService;
        this.afterSaleRequestService = afterSaleRequestService;
        this.requestIdentityResolver = requestIdentityResolver;
    }

    @GetMapping("/policies")
    @Operation(summary = "List after-sale policies", description = "Search after-sale policies by optional scene key")
    public ApiResponse<List<AfterSalePolicyResponse>> listPolicies(
        @Parameter(description = "Optional after-sale scene key", example = "refund_before_shipping")
        @RequestParam(value = "sceneKey", required = false) String sceneKey) {
        return ApiResponse.success(afterSaleService.listPolicies(sceneKey));
    }

    @GetMapping("/requests/{requestId}")
    @Operation(summary = "Get after-sale request", description = "Query one after-sale request by request ID")
    public ApiResponse<AfterSaleRequestResponse> getRequest(
        @PathVariable String requestId,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(afterSaleRequestService.getByRequestId(requestId, currentUserId));
    }

    @GetMapping("/requests")
    @Operation(summary = "List after-sale requests by order number")
    public ApiResponse<List<AfterSaleRequestResponse>> listRequests(
        @RequestParam("orderNo") String orderNo,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(afterSaleRequestService.listByOrderNo(orderNo, currentUserId));
    }

    @PostMapping("/requests")
    @Operation(summary = "Create after-sale request draft")
    public ApiResponse<AfterSaleRequestResponse> createRequest(
        @RequestBody AfterSaleRequestCreateRequest request,
        @RequestHeader(value = AgentServiceAuthenticationFilter.DELEGATED_USER_HEADER, required = false)
        String delegatedUserId,
        Authentication authentication) {
        String currentUserId = requestIdentityResolver.currentUserId(authentication, delegatedUserId);
        return ApiResponse.success(afterSaleRequestService.create(request, currentUserId));
    }
}
