package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.UserCoupon;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserCouponRepository extends JpaRepository<UserCoupon, Long> {

    List<UserCoupon> findByUserIdAndStatus(String userId, String status);
}
