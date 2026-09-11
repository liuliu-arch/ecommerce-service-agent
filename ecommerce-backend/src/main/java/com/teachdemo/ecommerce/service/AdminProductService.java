package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.AdminProductRequest;
import com.teachdemo.ecommerce.dto.AdminProductResponse;
import com.teachdemo.ecommerce.entity.Product;
import com.teachdemo.ecommerce.repository.ProductRepository;
import java.math.BigDecimal;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

@Service
public class AdminProductService {

    private static final String ON_SALE = "ON_SALE";
    private static final String OFF_SALE = "OFF_SALE";

    private final ProductRepository productRepository;

    public AdminProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<AdminProductResponse> list(String keyword, String category, String status) {
        return productRepository.findAll().stream()
            .filter(product -> matchesKeyword(product, keyword))
            .filter(product -> !StringUtils.hasText(category) || category.equalsIgnoreCase(product.getCategory()))
            .filter(product -> !StringUtils.hasText(status) || normalizeStatus(status).equals(toStatus(product)))
            .sorted(Comparator.comparing(Product::getUpdatedAt, Comparator.nullsLast(Comparator.naturalOrder())).reversed())
            .map(this::toResponse)
            .toList();
    }

    @Transactional
    public AdminProductResponse create(AdminProductRequest request) {
        validateProductRequest(request, true);
        String status = StringUtils.hasText(request.getStatus()) ? normalizeStatus(request.getStatus()) : OFF_SALE;
        String code = StringUtils.hasText(request.getCode()) ? request.getCode() : "SKU-ADMIN-" + (productRepository.count() + 1);
        productRepository.findByCode(code).ifPresent(product -> {
            throw BusinessException.badRequest("PRODUCT_CODE_DUPLICATED", "商品编码已存在");
        });
        Product product = new Product(code, request.getName(), request.getCategory(), request.getDescription(),
            request.getPrice(), request.getStockQuantity(), request.getHighlights(), ON_SALE.equals(status),
            Boolean.TRUE.equals(request.getSupportsSevenDayReturn()), request.getAfterSaleNote(),
            valueOrEmpty(request.getScenarioTags()));
        product.updateAdminFields(request.getName(), request.getCategory(), request.getDescription(), request.getPrice(),
            request.getStockQuantity(), request.getHighlights(), Boolean.TRUE.equals(request.getSupportsSevenDayReturn()),
            request.getAfterSaleNote(), valueOrEmpty(request.getScenarioTags()), valueOrEmpty(request.getImageUrl()));
        return toResponse(productRepository.save(product));
    }

    @Transactional
    public AdminProductResponse update(Long productId, AdminProductRequest request) {
        Product product = findProduct(productId);
        validateProductRequest(request, false);
        product.updateAdminFields(request.getName(), request.getCategory(), request.getDescription(), request.getPrice(),
            request.getStockQuantity(), request.getHighlights(), Boolean.TRUE.equals(request.getSupportsSevenDayReturn()),
            request.getAfterSaleNote(), valueOrEmpty(request.getScenarioTags()), valueOrEmpty(request.getImageUrl()));
        if (StringUtils.hasText(request.getStatus())) {
            if (ON_SALE.equals(normalizeStatus(request.getStatus()))) {
                product.publish();
            } else {
                product.unpublish();
            }
        }
        return toResponse(product);
    }

    @Transactional
    public AdminProductResponse publish(Long productId) {
        Product product = findProduct(productId);
        product.publish();
        return toResponse(product);
    }

    @Transactional
    public AdminProductResponse unpublish(Long productId) {
        Product product = findProduct(productId);
        product.unpublish();
        return toResponse(product);
    }

    private Product findProduct(Long productId) {
        return productRepository.findById(productId)
            .orElseThrow(() -> BusinessException.notFound("PRODUCT_NOT_FOUND", "商品不存在"));
    }

    private boolean matchesKeyword(Product product, String keyword) {
        if (!StringUtils.hasText(keyword)) {
            return true;
        }
        String normalized = keyword.toLowerCase(Locale.ROOT);
        return contains(product.getName(), normalized) || contains(product.getDescription(), normalized);
    }

    private boolean contains(String value, String keyword) {
        return value != null && value.toLowerCase(Locale.ROOT).contains(keyword);
    }

    private void validateProductRequest(AdminProductRequest request, boolean requireStatus) {
        if (!StringUtils.hasText(request.getName())) {
            throw BusinessException.badRequest("PRODUCT_NAME_REQUIRED", "商品名称不能为空");
        }
        if (request.getPrice() == null || request.getPrice().compareTo(BigDecimal.ZERO) < 0) {
            throw BusinessException.badRequest("PRODUCT_PRICE_INVALID", "商品价格不能小于 0");
        }
        if (request.getStockQuantity() == null || request.getStockQuantity() < 0) {
            throw BusinessException.badRequest("PRODUCT_STOCK_INVALID", "商品库存不能小于 0");
        }
        if (requireStatus || StringUtils.hasText(request.getStatus())) {
            normalizeStatus(request.getStatus());
        }
    }

    private String normalizeStatus(String status) {
        if (!StringUtils.hasText(status)) {
            return OFF_SALE;
        }
        String normalized = status.toUpperCase(Locale.ROOT);
        if (!ON_SALE.equals(normalized) && !OFF_SALE.equals(normalized)) {
            throw BusinessException.badRequest("PRODUCT_STATUS_INVALID", "商品状态只能为 ON_SALE 或 OFF_SALE");
        }
        return normalized;
    }

    private String toStatus(Product product) {
        return Boolean.TRUE.equals(product.getActive()) ? ON_SALE : OFF_SALE;
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }

    private AdminProductResponse toResponse(Product product) {
        return new AdminProductResponse(product.getId(), product.getCode(), product.getName(), product.getCategory(),
            product.getDescription(), product.getPrice(), product.getStock(), product.getHighlights(), toStatus(product),
            product.getImageUrl(), product.getReturnable(), product.getAfterSaleLimit(), product.getScenarioTags(),
            product.getCreatedAt(), product.getUpdatedAt());
    }
}
