package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.AdminPromotionProductRequest;
import com.teachdemo.ecommerce.dto.AdminPromotionProductResponse;
import com.teachdemo.ecommerce.dto.AdminPromotionRequest;
import com.teachdemo.ecommerce.dto.AdminPromotionResponse;
import com.teachdemo.ecommerce.entity.Product;
import com.teachdemo.ecommerce.entity.ProductPromotion;
import com.teachdemo.ecommerce.repository.ProductPromotionRepository;
import com.teachdemo.ecommerce.repository.ProductRepository;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class AdminPromotionService {

    private final ProductPromotionRepository productPromotionRepository;
    private final ProductRepository productRepository;

    public AdminPromotionService(ProductPromotionRepository productPromotionRepository,
                                 ProductRepository productRepository) {
        this.productPromotionRepository = productPromotionRepository;
        this.productRepository = productRepository;
    }

    public List<AdminPromotionResponse> list(String keyword) {
        return groupedPromotions().values().stream()
            .filter(promotions -> matchesKeyword(promotions.get(0), keyword))
            .map(promotions -> toResponse(promotions, false))
            .sorted(Comparator.comparing(AdminPromotionResponse::getStartAt, Comparator.nullsLast(Comparator.naturalOrder())).reversed())
            .toList();
    }

    public AdminPromotionResponse get(String promotionName) {
        List<ProductPromotion> promotions = productPromotionRepository.findByPromotionName(promotionName);
        if (promotions.isEmpty()) {
            throw BusinessException.notFound("PROMOTION_NOT_FOUND", "活动不存在");
        }
        return toResponse(promotions, true);
    }

    @Transactional
    public AdminPromotionResponse create(AdminPromotionRequest request) {
        validateRequest(request);
        String promotionName = request.getPromotionName().trim();
        if (!productPromotionRepository.findByPromotionName(promotionName).isEmpty()) {
            throw BusinessException.badRequest("PROMOTION_NAME_DUPLICATED", "活动名称已存在");
        }
        savePromotionProducts(List.of(), promotionName, request);
        return get(promotionName);
    }

    @Transactional
    public AdminPromotionResponse update(String oldPromotionName, AdminPromotionRequest request) {
        List<ProductPromotion> existing = productPromotionRepository.findByPromotionName(oldPromotionName);
        if (existing.isEmpty()) {
            throw BusinessException.notFound("PROMOTION_NOT_FOUND", "活动不存在");
        }
        validateRequest(request);
        String newPromotionName = request.getPromotionName().trim();
        if (!oldPromotionName.equals(newPromotionName) && !productPromotionRepository.findByPromotionName(newPromotionName).isEmpty()) {
            throw BusinessException.badRequest("PROMOTION_NAME_DUPLICATED", "活动名称已存在");
        }
        savePromotionProducts(existing, newPromotionName, request);
        return get(newPromotionName);
    }

    private Map<String, List<ProductPromotion>> groupedPromotions() {
        return productPromotionRepository.findAll().stream()
            .collect(Collectors.groupingBy(ProductPromotion::getPromotionName, LinkedHashMap::new, Collectors.toList()));
    }

    private boolean matchesKeyword(ProductPromotion promotion, String keyword) {
        if (!StringUtils.hasText(keyword)) {
            return true;
        }
        String normalized = keyword.toLowerCase();
        return contains(promotion.getPromotionName(), normalized)
            || contains(promotion.getPromotionType(), normalized)
            || contains(promotion.getDiscountSummary(), normalized);
    }

    private boolean contains(String value, String keyword) {
        return value != null && value.toLowerCase().contains(keyword);
    }

    private void validateRequest(AdminPromotionRequest request) {
        if (!StringUtils.hasText(request.getPromotionName())) {
            throw BusinessException.badRequest("PROMOTION_NAME_REQUIRED", "活动名称不能为空");
        }
        if (!StringUtils.hasText(request.getPromotionType())) {
            throw BusinessException.badRequest("PROMOTION_TYPE_REQUIRED", "活动类型不能为空");
        }
        if (!StringUtils.hasText(request.getDiscountSummary())) {
            throw BusinessException.badRequest("PROMOTION_SUMMARY_REQUIRED", "活动说明不能为空");
        }
        if (request.getStartAt() != null && request.getEndAt() != null && request.getEndAt().isBefore(request.getStartAt())) {
            throw BusinessException.badRequest("PROMOTION_TIME_INVALID", "活动结束时间不能早于开始时间");
        }
        if (request.getProducts() == null || request.getProducts().isEmpty()) {
            throw BusinessException.badRequest("PROMOTION_PRODUCTS_REQUIRED", "活动至少需要选择一个商品");
        }
    }

    private void savePromotionProducts(List<ProductPromotion> existing, String promotionName, AdminPromotionRequest request) {
        Map<Long, AdminPromotionProductRequest> requestedProducts = new LinkedHashMap<>();
        for (AdminPromotionProductRequest productRequest : request.getProducts()) {
            if (productRequest.getProductId() == null) {
                throw BusinessException.badRequest("PROMOTION_PRODUCT_REQUIRED", "活动商品不能为空");
            }
            requestedProducts.put(productRequest.getProductId(), productRequest);
        }

        Map<Long, ProductPromotion> existingByProductId = existing.stream()
            .collect(Collectors.toMap(ProductPromotion::getProductId, Function.identity(), (left, right) -> right));
        Set<Long> requestedProductIds = requestedProducts.keySet();
        List<ProductPromotion> removed = existing.stream()
            .filter(promotion -> !requestedProductIds.contains(promotion.getProductId()))
            .toList();
        productPromotionRepository.deleteAll(removed);

        for (AdminPromotionProductRequest productRequest : requestedProducts.values()) {
            Product product = productRepository.findById(productRequest.getProductId())
                .orElseThrow(() -> BusinessException.notFound("PRODUCT_NOT_FOUND", "商品不存在"));
            BigDecimal promotionPrice = productRequest.getPromotionPrice() == null ? product.getPrice() : productRequest.getPromotionPrice();
            if (promotionPrice.compareTo(BigDecimal.ZERO) < 0) {
                throw BusinessException.badRequest("PROMOTION_PRICE_INVALID", "活动价不能小于 0");
            }
            ProductPromotion promotion = existingByProductId.get(product.getId());
            if (promotion == null) {
                promotion = new ProductPromotion(product.getId(), promotionName, request.getPromotionType(),
                    request.getDiscountSummary(), promotionPrice, request.getRequiredMemberLevel(), valueOrEmpty(request.getConditionSummary()),
                    request.getStartAt(), request.getEndAt(), Boolean.TRUE.equals(request.getActive()));
            } else {
                promotion.updatePromotionFacts(promotionName, request.getPromotionType(), request.getDiscountSummary(),
                    promotionPrice, request.getRequiredMemberLevel(), valueOrEmpty(request.getConditionSummary()),
                    request.getStartAt(), request.getEndAt(), Boolean.TRUE.equals(request.getActive()));
            }
            productPromotionRepository.save(promotion);
        }
    }

    private AdminPromotionResponse toResponse(List<ProductPromotion> promotions, boolean includeAllProducts) {
        ProductPromotion first = promotions.get(0);
        Map<Long, ProductPromotion> promotionByProductId = promotions.stream()
            .collect(Collectors.toMap(ProductPromotion::getProductId, Function.identity(), (left, right) -> right));
        List<Product> products = includeAllProducts ? productRepository.findAll() : productRepository.findAllById(promotionByProductId.keySet());
        List<AdminPromotionProductResponse> productResponses = products.stream()
            .sorted(Comparator.comparing(Product::getId))
            .map(product -> {
                ProductPromotion promotion = promotionByProductId.get(product.getId());
                return new AdminPromotionProductResponse(
                    product.getId(),
                    product.getCode(),
                    product.getName(),
                    product.getCategory(),
                    product.getPrice(),
                    promotion == null ? null : promotion.getPromotionPrice(),
                    promotion != null
                );
            })
            .toList();
        return new AdminPromotionResponse(
            first.getPromotionName(),
            first.getPromotionType(),
            first.getDiscountSummary(),
            first.getRequiredMemberLevel(),
            first.getConditionSummary(),
            first.getStartAt(),
            first.getEndAt(),
            Boolean.TRUE.equals(first.getActive()),
            promotions.size(),
            productResponses
        );
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }
}
