package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.OrderEntity;
import com.teachdemo.ecommerce.entity.OrderItem;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderItemRepository extends JpaRepository<OrderItem, Long> {

    List<OrderItem> findByOrderEntity(OrderEntity orderEntity);
}
