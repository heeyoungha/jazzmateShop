package shop.jazzmate.jazzmateshop.common.exception;

/**
 * 비즈니스 로직 위반 시 발생하는 예외
 * HTTP 400 Bad Request로 매핑
 */
public class BusinessException extends RuntimeException {
    public BusinessException(String message) {
        super(message);
    }
}
