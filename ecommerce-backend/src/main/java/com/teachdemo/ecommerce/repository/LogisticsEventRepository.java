package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.LogisticsEvent;
import com.teachdemo.ecommerce.entity.LogisticsInfo;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LogisticsEventRepository extends JpaRepository<LogisticsEvent, Long> {

    List<LogisticsEvent> findByLogisticsInfoOrderByOccurredAtDesc(LogisticsInfo logisticsInfo);
}
