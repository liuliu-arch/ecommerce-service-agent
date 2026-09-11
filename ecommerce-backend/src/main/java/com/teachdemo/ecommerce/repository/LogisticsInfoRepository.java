package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.LogisticsInfo;
import com.teachdemo.ecommerce.entity.OrderEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LogisticsInfoRepository extends JpaRepository<LogisticsInfo, Long> {

    Optional<LogisticsInfo> findByOrderEntity(OrderEntity orderEntity);
}
