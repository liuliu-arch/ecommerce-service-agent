package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.BalanceResponse;
import com.teachdemo.ecommerce.dto.BalanceTransactionResponse;
import com.teachdemo.ecommerce.dto.CartItemRequest;
import com.teachdemo.ecommerce.dto.CartItemUpdateRequest;
import com.teachdemo.ecommerce.dto.CartResponse;
import com.teachdemo.ecommerce.dto.CreateOrderRequest;
import com.teachdemo.ecommerce.dto.PaymentResponse;
import com.teachdemo.ecommerce.dto.ShopAfterSaleCreateRequest;
import com.teachdemo.ecommerce.dto.ShopAfterSaleResponse;
import com.teachdemo.ecommerce.dto.ShopOrderResponse;
import com.teachdemo.ecommerce.dto.ShopProductResponse;
import com.teachdemo.ecommerce.security.AccountPrincipal;
import com.teachdemo.ecommerce.service.ShopService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Shop APIs", description = "电商公司用户商城商品、购物车、订单、余额和售后接口")
@RestController
@RequestMapping("/api/shop")
public class ShopController {

    private final ShopService shopService;

    public ShopController(ShopService shopService) {
        this.shopService = shopService;
    }

    @GetMapping("/products")
    @Operation(summary = "List on-sale products")
    public ApiResponse<List<ShopProductResponse>> listProducts(
        @RequestParam(value = "keyword", required = false) String keyword,
        @RequestParam(value = "category", required = false) String category,
        @RequestParam(value = "page", required = false) Integer page,
        @RequestParam(value = "size", required = false) Integer size) {
        return ApiResponse.success(shopService.listProducts(keyword, category));
    }

    @GetMapping("/products/{productId}")
    @Operation(summary = "Get on-sale product details")
    public ApiResponse<ShopProductResponse> getProduct(@PathVariable Long productId) {
        return ApiResponse.success(shopService.getProduct(productId));
    }

    @GetMapping("/cart")
    @Operation(summary = "Get current user's cart")
    public ApiResponse<CartResponse> getCart(@AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(shopService.getCart(principal.getUserId()));
    }

    @PostMapping("/cart/items")
    @Operation(summary = "Add product to current user's cart")
    public ApiResponse<CartResponse> addCartItem(@AuthenticationPrincipal AccountPrincipal principal,
                                                 @Valid @RequestBody CartItemRequest request) {
        return ApiResponse.success(shopService.addCartItem(principal.getUserId(), request));
    }

    @PatchMapping("/cart/items/{itemId}")
    @Operation(summary = "Update current user's cart item")
    public ApiResponse<CartResponse> updateCartItem(@AuthenticationPrincipal AccountPrincipal principal,
                                                    @PathVariable Long itemId,
                                                    @Valid @RequestBody CartItemUpdateRequest request) {
        return ApiResponse.success(shopService.updateCartItem(principal.getUserId(), itemId, request));
    }

    @DeleteMapping("/cart/items/{itemId}")
    @Operation(summary = "Delete current user's cart item")
    public ApiResponse<Void> deleteCartItem(@AuthenticationPrincipal AccountPrincipal principal,
                                            @PathVariable Long itemId) {
        shopService.deleteCartItem(principal.getUserId(), itemId);
        return ApiResponse.success(null);
    }

    @PostMapping("/orders")
    @Operation(summary = "Create current user's order")
    public ApiResponse<ShopOrderResponse> createOrder(@AuthenticationPrincipal AccountPrincipal principal,
                                                      @Valid @RequestBody CreateOrderRequest request) {
        return ApiResponse.success(shopService.createOrder(principal.getUserId(), request));
    }

    @GetMapping("/orders")
    @Operation(summary = "List current user's orders")
    public ApiResponse<List<ShopOrderResponse>> listOrders(@AuthenticationPrincipal AccountPrincipal principal,
                                                           @RequestParam(value = "status", required = false) String status,
                                                           @RequestParam(value = "page", required = false) Integer page,
                                                           @RequestParam(value = "size", required = false) Integer size) {
        return ApiResponse.success(shopService.listOrders(principal.getUserId(), status));
    }

    @GetMapping("/orders/{orderNo}")
    @Operation(summary = "Get current user's order details")
    public ApiResponse<ShopOrderResponse> getOrder(@AuthenticationPrincipal AccountPrincipal principal,
                                                   @PathVariable String orderNo) {
        return ApiResponse.success(shopService.getOrder(principal.getUserId(), orderNo));
    }

    @PostMapping("/orders/{orderNo}/pay")
    @Operation(summary = "Pay current user's order with balance")
    public ApiResponse<PaymentResponse> pay(@AuthenticationPrincipal AccountPrincipal principal,
                                            @PathVariable String orderNo) {
        return ApiResponse.success(shopService.pay(principal.getUserId(), orderNo));
    }

    @GetMapping("/balance")
    @Operation(summary = "Get current user's balance")
    public ApiResponse<BalanceResponse> getBalance(@AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(shopService.getBalance(principal.getUserId()));
    }

    @GetMapping("/balance/transactions")
    @Operation(summary = "List current user's balance transactions")
    public ApiResponse<List<BalanceTransactionResponse>> listBalanceTransactions(
        @AuthenticationPrincipal AccountPrincipal principal,
        @RequestParam(value = "type", required = false) String type,
        @RequestParam(value = "page", required = false) Integer page,
        @RequestParam(value = "size", required = false) Integer size) {
        return ApiResponse.success(shopService.listBalanceTransactions(principal.getUserId(), type));
    }

    @PostMapping("/after-sales")
    @Operation(summary = "Create current user's after-sale request")
    public ApiResponse<ShopAfterSaleResponse> createAfterSale(
        @AuthenticationPrincipal AccountPrincipal principal,
        @Valid @RequestBody ShopAfterSaleCreateRequest request) {
        return ApiResponse.success(shopService.createAfterSale(principal.getUserId(), request));
    }

    @GetMapping("/after-sales")
    @Operation(summary = "List current user's after-sale requests")
    public ApiResponse<List<ShopAfterSaleResponse>> listAfterSales(@AuthenticationPrincipal AccountPrincipal principal) {
        return ApiResponse.success(shopService.listAfterSales(principal.getUserId()));
    }
}
