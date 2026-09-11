package com.teachdemo.ecommerce.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Common API response wrapper")
public class ApiResponse<T> {

    @Schema(description = "Whether the request succeeds", example = "true")
    private final boolean success;
    @Schema(description = "Business status code", example = "OK")
    private final String code;
    @Schema(description = "Status message", example = "success")
    private final String message;
    @Schema(description = "Payload data")
    private final T data;

    private ApiResponse(boolean success, String code, String message, T data) {
        this.success = success;
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<T>(true, "OK", "success", data);
    }

    public static <T> ApiResponse<T> error(String code, String message) {
        return new ApiResponse<T>(false, code, message, null);
    }

    public boolean isSuccess() {
        return success;
    }

    public String getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    public T getData() {
        return data;
    }
}
