package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "FAQ entry")
public class FaqResponse {

    @Schema(description = "Category", example = "Invoice")
    private final String category;
    @Schema(description = "Question", example = "When will the invoice be issued?")
    private final String question;
    @Schema(description = "Answer", example = "It is issued within 3 business days after delivery")
    private final String answer;

    public FaqResponse(String category, String question, String answer) {
        this.category = category;
        this.question = question;
        this.answer = answer;
    }

    public String getCategory() {
        return category;
    }

    public String getQuestion() {
        return question;
    }

    public String getAnswer() {
        return answer;
    }
}
