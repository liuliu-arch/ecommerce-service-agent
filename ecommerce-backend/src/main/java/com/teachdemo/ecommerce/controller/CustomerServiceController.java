package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.CustomerServiceChatRequest;
import com.teachdemo.ecommerce.dto.CustomerServiceResponse;
import com.teachdemo.ecommerce.dto.CustomerServiceResumeRequest;
import com.teachdemo.ecommerce.security.AccountPrincipal;
import com.teachdemo.ecommerce.service.CustomerServiceException;
import com.teachdemo.ecommerce.service.CustomerServiceGatewayService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Customer Service", description = "电商公司商城客服 Agent 网关")
@RestController
@RequestMapping("/api/customer-service")
public class CustomerServiceController {

    private final CustomerServiceGatewayService customerServiceGatewayService;

    public CustomerServiceController(CustomerServiceGatewayService customerServiceGatewayService) {
        this.customerServiceGatewayService = customerServiceGatewayService;
    }

    @PostMapping("/chat")
    @Operation(summary = "Chat with customer service Agent through ecommerce backend")
    public ApiResponse<CustomerServiceResponse> chat(@Valid @RequestBody CustomerServiceChatRequest request,
                                                     @AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(customerServiceGatewayService.chat(request, principal));
    }

    @PostMapping("/resume")
    @Operation(summary = "Resume a confirmed customer-service action")
    public ApiResponse<CustomerServiceResponse> resume(@Valid @RequestBody CustomerServiceResumeRequest request,
                                                       @AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(customerServiceGatewayService.resume(request, principal));
    }

    @ExceptionHandler(CustomerServiceException.class)
    public ResponseEntity<ApiResponse<Void>> handleCustomerServiceException(CustomerServiceException ex) {
        return ResponseEntity.status(ex.getStatus()).body(ApiResponse.error(ex.getCode(), ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation() {
        return ResponseEntity.badRequest().body(ApiResponse.error("BAD_REQUEST", "请求参数不完整"));
    }
}
