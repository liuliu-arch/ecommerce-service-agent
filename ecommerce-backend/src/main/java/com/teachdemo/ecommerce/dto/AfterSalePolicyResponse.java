package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "After-sale policy")
public class AfterSalePolicyResponse {

    @Schema(description = "Policy scene key", example = "refund_before_shipping")
    private final String sceneKey;
    @Schema(description = "Policy title", example = "Refund before shipping")
    private final String title;
    @Schema(description = "Policy content", example = "Orders can be refunded before shipment")
    private final String content;
    @Schema(description = "Eligibility", example = "Order status is pending shipment")
    private final String eligibility;
    private final String applicableConditions;
    private final String exclusionConditions;
    private final String requiredEvidence;
    private final Boolean requiresManualReview;
    private final String suggestedAction;
    private final String policyVersion;

    public AfterSalePolicyResponse(String sceneKey, String title, String content, String eligibility) {
        this(sceneKey, title, content, eligibility, eligibility, "", "", false, "", "v1");
    }

    public AfterSalePolicyResponse(String sceneKey, String title, String content, String eligibility,
                                   String applicableConditions, String exclusionConditions, String requiredEvidence,
                                   Boolean requiresManualReview, String suggestedAction, String policyVersion) {
        this.sceneKey = sceneKey;
        this.title = title;
        this.content = content;
        this.eligibility = eligibility;
        this.applicableConditions = applicableConditions;
        this.exclusionConditions = exclusionConditions;
        this.requiredEvidence = requiredEvidence;
        this.requiresManualReview = requiresManualReview;
        this.suggestedAction = suggestedAction;
        this.policyVersion = policyVersion;
    }

    public String getSceneKey() {
        return sceneKey;
    }

    public String getTitle() {
        return title;
    }

    public String getContent() {
        return content;
    }

    public String getEligibility() {
        return eligibility;
    }

    public String getApplicableConditions() {
        return applicableConditions;
    }

    public String getExclusionConditions() {
        return exclusionConditions;
    }

    public String getRequiredEvidence() {
        return requiredEvidence;
    }

    public Boolean getRequiresManualReview() {
        return requiresManualReview;
    }

    public String getSuggestedAction() {
        return suggestedAction;
    }

    public String getPolicyVersion() {
        return policyVersion;
    }
}
