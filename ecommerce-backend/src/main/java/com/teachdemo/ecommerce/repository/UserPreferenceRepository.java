package com.teachdemo.ecommerce.repository;

import com.teachdemo.ecommerce.entity.UserPreference;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserPreferenceRepository extends JpaRepository<UserPreference, Long> {

    Optional<UserPreference> findByUserId(String userId);
}
