package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.DemoUserCreateRequest;
import com.teachdemo.ecommerce.dto.DemoUserResponse;
import com.teachdemo.ecommerce.dto.UserPreferenceRequest;
import com.teachdemo.ecommerce.dto.UserPreferenceResponse;
import com.teachdemo.ecommerce.dto.UserCouponResponse;
import com.teachdemo.ecommerce.dto.UserProfileResponse;
import com.teachdemo.ecommerce.entity.UserCoupon;
import com.teachdemo.ecommerce.entity.UserPreference;
import com.teachdemo.ecommerce.entity.UserProfile;
import com.teachdemo.ecommerce.repository.UserCouponRepository;
import com.teachdemo.ecommerce.repository.UserPreferenceRepository;
import com.teachdemo.ecommerce.repository.UserProfileRepository;
import java.util.Arrays;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class UserService {

    private final UserProfileRepository userProfileRepository;
    private final UserPreferenceRepository userPreferenceRepository;
    private final UserCouponRepository userCouponRepository;

    public UserService(UserProfileRepository userProfileRepository,
                       UserPreferenceRepository userPreferenceRepository,
                       UserCouponRepository userCouponRepository) {
        this.userProfileRepository = userProfileRepository;
        this.userPreferenceRepository = userPreferenceRepository;
        this.userCouponRepository = userCouponRepository;
    }

    public UserProfileResponse getProfile(String userId) {
        UserProfile profile = userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        return toProfileResponse(profile);
    }

    public UserPreferenceResponse getPreference(String userId) {
        UserPreference preference = userPreferenceRepository.findByUserId(userId)
            .orElseThrow(() -> new IllegalArgumentException("User preference not found: " + userId));
        return toPreferenceResponse(preference);
    }

    public List<UserCouponResponse> listCoupons(String userId, String productCategory) {
        userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        return userCouponRepository.findByUserIdAndStatus(userId, "available").stream()
            .filter(coupon -> matchesCategory(coupon, productCategory))
            .map(this::toCouponResponse)
            .toList();
    }

    public UserPreferenceResponse savePreference(String userId, UserPreferenceRequest request) {
        userProfileRepository.findByUserId(userId)
            .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        UserPreference preference = userPreferenceRepository.findByUserId(userId)
            .orElseGet(() -> new UserPreference(userId, "", "", null, null, false));
        preference.update(request.getPreferredCategories(), request.getPreferredDelivery(),
            request.getBudgetMin(), request.getBudgetMax(), request.getInvoiceRequired());
        return toPreferenceResponse(userPreferenceRepository.save(preference));
    }

    public DemoUserResponse createDemoUser(DemoUserCreateRequest request) {
        if (request.getUserId() == null || request.getUserId().isBlank()) {
            throw new IllegalArgumentException("userId is required");
        }
        userProfileRepository.findByUserId(request.getUserId()).ifPresent(profile -> {
            throw new IllegalArgumentException("User already exists: " + request.getUserId());
        });
        UserProfile profile = userProfileRepository.save(new UserProfile(
            request.getUserId(),
            request.getNickname(),
            null,
            request.getMemberLevel(),
            request.getRiskLevel()
        ));
        UserPreference preference = userPreferenceRepository.save(new UserPreference(
            request.getUserId(),
            request.getPreferredCategories(),
            request.getPreferredDelivery(),
            request.getBudgetMin(),
            request.getBudgetMax(),
            request.getInvoiceRequired()
        ));
        return new DemoUserResponse(toProfileResponse(profile), toPreferenceResponse(preference));
    }

    private UserProfileResponse toProfileResponse(UserProfile profile) {
        return new UserProfileResponse(profile.getUserId(), profile.getNickname(), profile.getMobile(),
            profile.getMemberLevel(), profile.getRiskLevel());
    }

    private UserPreferenceResponse toPreferenceResponse(UserPreference preference) {
        return new UserPreferenceResponse(preference.getUserId(), preference.getPreferredCategories(),
            preference.getPreferredDelivery(), preference.getBudgetMin(), preference.getBudgetMax(),
            preference.getInvoiceRequired());
    }

    private UserCouponResponse toCouponResponse(UserCoupon coupon) {
        return new UserCouponResponse(
            coupon.getCouponCode(),
            coupon.getCouponName(),
            coupon.getCouponType(),
            coupon.getDiscountAmount(),
            coupon.getThresholdAmount(),
            coupon.getApplicableCategories(),
            coupon.getStartAt(),
            coupon.getEndAt(),
            coupon.getStatus()
        );
    }

    private boolean matchesCategory(UserCoupon coupon, String productCategory) {
        if (!StringUtils.hasText(productCategory)) {
            return true;
        }
        String normalizedCategory = productCategory.trim();
        return Arrays.stream(String.valueOf(coupon.getApplicableCategories()).split(","))
            .map(String::trim)
            .anyMatch(category -> "全部".equals(category) || category.equalsIgnoreCase(normalizedCategory));
    }
}
