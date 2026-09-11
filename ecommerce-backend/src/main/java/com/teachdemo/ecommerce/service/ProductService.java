package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.ProductResponse;
import com.teachdemo.ecommerce.dto.ProductPromotionResponse;
import com.teachdemo.ecommerce.entity.Product;
import com.teachdemo.ecommerce.entity.ProductPromotion;
import com.teachdemo.ecommerce.repository.ProductPromotionRepository;
import com.teachdemo.ecommerce.repository.ProductRepository;
import java.time.Clock;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class ProductService {

    private final ProductRepository productRepository;
    private final ProductPromotionRepository productPromotionRepository;
    private final Clock clock;

    public ProductService(ProductRepository productRepository, ProductPromotionRepository productPromotionRepository,
                          Clock clock) {
        this.productRepository = productRepository;
        this.productPromotionRepository = productPromotionRepository;
        this.clock = clock;
    }

    public List<ProductResponse> listProducts(String keyword) {
        List<Product> products;
        if (StringUtils.hasText(keyword)) {
            products = productRepository.findByNameContainingIgnoreCaseOrDescriptionContainingIgnoreCase(keyword, keyword);
        } else {
            products = productRepository.findAll();
        }
        Map<Long, ProductPromotion> promotions = activePromotions(products);
        return products.stream().map(product -> toResponse(product, promotions.get(product.getId()))).collect(Collectors.toList());
    }

    public ProductResponse getProduct(Long id) {
        Product product = productRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Product not found: " + id));
        ProductPromotion promotion = activePromotions(List.of(product)).get(product.getId());
        return toResponse(product, promotion);
    }

    private Map<Long, ProductPromotion> activePromotions(List<Product> products) {
        List<Long> productIds = products.stream().map(Product::getId).collect(Collectors.toList());
        if (productIds.isEmpty()) {
            return Map.of();
        }
        // 商品促销与价格、库存属于同一类业务事实：Agent 应通过 Tool 获取，而不是让模型从知识库里猜。
        LocalDateTime now = LocalDateTime.now(clock);
        return productPromotionRepository.findByProductIdInAndActiveTrue(productIds).stream()
            .filter(promotion -> promotionEffectiveAt(promotion, now))
            .collect(Collectors.toMap(ProductPromotion::getProductId, promotion -> promotion,
                (left, right) -> left.getId() > right.getId() ? left : right));
    }

    private boolean promotionEffectiveAt(ProductPromotion promotion, LocalDateTime now) {
        return (promotion.getStartAt() == null || !promotion.getStartAt().isAfter(now))
            && (promotion.getEndAt() == null || !promotion.getEndAt().isBefore(now));
    }

    private ProductResponse toResponse(Product product, ProductPromotion promotion) {
        return new ProductResponse(product.getId(), product.getCode(), product.getName(), product.getCategory(),
            product.getDescription(), product.getPrice(), product.getStock(), product.getHighlights(),
            product.getActive(), product.getReturnable(), product.getAfterSaleLimit(), product.getScenarioTags(),
            promotion == null ? null : toPromotionResponse(promotion));
    }

    private ProductPromotionResponse toPromotionResponse(ProductPromotion promotion) {
        return new ProductPromotionResponse(
            promotion.getId(),
            promotion.getPromotionName(),
            promotion.getPromotionType(),
            promotion.getDiscountSummary(),
            promotion.getPromotionPrice(),
            promotion.getRequiredMemberLevel(),
            promotion.getConditionSummary(),
            promotion.getStartAt(),
            promotion.getEndAt()
        );
    }
}
