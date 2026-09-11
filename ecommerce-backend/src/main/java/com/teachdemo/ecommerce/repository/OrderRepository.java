package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.OrderEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<OrderEntity, Long> {

    Optional<OrderEntity> findByOrderNo(String orderNo);

    Optional<OrderEntity> findByOrderNoAndUserId(String orderNo, String userId);

    List<OrderEntity> findByUserIdOrderByCreatedAtDesc(String userId);

    List<OrderEntity> findByUserIdAndStatusOrderByCreatedAtDesc(String userId, String status);
}
