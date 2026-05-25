package shop.jazzmate.jazzmateshop.common.dto;

import lombok.Getter;

@Getter
public class ErrorResponse {
    private final boolean success = false;
    private final String message;

    public ErrorResponse(String message) {
        this.message = message;
    }
}
