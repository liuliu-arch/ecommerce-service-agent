package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.ProductPromotion;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductPromotionRepository extends JpaRepository<ProductPromotion, Long> {

    List<ProductPromotion> findByProductIdInAndActiveTrue(Collection<Long> productIds);

    List<ProductPromotion> findByProductIdAndActiveTrue(Long productId);

    List<ProductPromotion> findByPromotionName(String promotionName);

    Optional<ProductPromotion> findByProductIdAndPromotionName(Long productId, String promotionName);

    boolean existsByProductIdAndPromotionName(Long productId, String promotionName);
}
