package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.BalanceAccount;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BalanceAccountRepository extends JpaRepository<BalanceAccount, Long> {

    Optional<BalanceAccount> findByUserId(String userId);
}
