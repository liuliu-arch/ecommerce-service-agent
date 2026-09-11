package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.ProductResponse;
import com.teachdemo.ecommerce.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Products", description = "查询电商公司商品、库存和活动信息")
@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping
    @Operation(summary = "List products", description = "Browse products and optionally filter them by keyword")
    public ApiResponse<List<ProductResponse>> listProducts(
        @Parameter(description = "Optional product keyword", example = "headphone")
        @RequestParam(value = "keyword", required = false) String keyword) {
        return ApiResponse.success(productService.listProducts(keyword));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get product details", description = "Query a single product by its ID")
    public ApiResponse<ProductResponse> getProduct(
        @Parameter(description = "Product ID", example = "1")
        @PathVariable Long id) {
        return ApiResponse.success(productService.getProduct(id));
    }
}
