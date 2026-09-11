package com.teachdemo.ecommerce.controller;

import com.teachdemo.ecommerce.dto.ApiResponse;
import com.teachdemo.ecommerce.dto.FaqResponse;
import com.teachdemo.ecommerce.service.FaqService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "FAQ", description = "Search invoice, shipping, and after-sale FAQ entries")
@RestController
@RequestMapping("/api/faq")
public class FaqController {

    private final FaqService faqService;

    public FaqController(FaqService faqService) {
        this.faqService = faqService;
    }

    @GetMapping
    @Operation(summary = "List FAQ entries", description = "Search common questions by optional keyword")
    public ApiResponse<List<FaqResponse>> listFaq(
        @Parameter(description = "Optional FAQ keyword", example = "invoice")
        @RequestParam(value = "keyword", required = false) String keyword) {
        return ApiResponse.success(faqService.listFaq(keyword));
    }
}
