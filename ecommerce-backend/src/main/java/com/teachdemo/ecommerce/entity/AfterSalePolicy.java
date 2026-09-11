package com.teachdemo.ecommerce.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;

@Entity
public class AfterSalePolicy {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String sceneKey;

    private String title;

    @Column(length = 1500)
    private String content;

    private String eligibility;

    @Column(length = 1000)
    private String applicableConditions;

    @Column(length = 1000)
    private String exclusionConditions;

    private String requiredEvidence;

    private Boolean requiresManualReview;

    private String suggestedAction;

    private String policyVersion;

    protected AfterSalePolicy() {
    }

    public AfterSalePolicy(String sceneKey, String title, String content, String eligibility) {
        this(sceneKey, title, content, eligibility, eligibility, "", "", false, "", "v1");
    }

    public AfterSalePolicy(String sceneKey, String title, String content, String eligibility,
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

    public Long getId() {
        return id;
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
