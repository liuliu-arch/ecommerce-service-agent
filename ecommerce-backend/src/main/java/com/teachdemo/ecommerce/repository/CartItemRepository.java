package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.CartItem;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CartItemRepository extends JpaRepository<CartItem, Long> {

    List<CartItem> findByUserId(String userId);

    Optional<CartItem> findByIdAndUserId(Long id, String userId);

    Optional<CartItem> findByUserIdAndProductId(String userId, Long productId);

    List<CartItem> findByIdInAndUserId(List<Long> ids, String userId);
}
