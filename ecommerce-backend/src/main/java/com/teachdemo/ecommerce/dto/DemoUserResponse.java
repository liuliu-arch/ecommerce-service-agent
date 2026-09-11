package com.teachdemo.ecommerce.dto;

public class DemoUserResponse {

    private final UserProfileResponse profile;
    private final UserPreferenceResponse preferences;

    public DemoUserResponse(UserProfileResponse profile, UserPreferenceResponse preferences) {
        this.profile = profile;
        this.preferences = preferences;
    }

    public UserProfileResponse getProfile() {
        return profile;
    }

    public UserPreferenceResponse getPreferences() {
        return preferences;
    }
}
