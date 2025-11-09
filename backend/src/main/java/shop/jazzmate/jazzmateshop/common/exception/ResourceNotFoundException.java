package shop.jazzmate.jazzmateshop.common.exception;

/**
 * 리소스를 찾을 수 없을 때 발생하는 예외
 * HTTP 404 Not Found로 매핑
 */
public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) {
        super(message);
    }
    
    /**
     * 편의 메서드: 리소스 이름과 ID로 예외 생성
     * 
     * @param resourceName 리소스 이름 (예: "감상문", "사용자")
     * @param id 리소스 ID
     * @return ResourceNotFoundException 인스턴스
     */
    public static ResourceNotFoundException of(String resourceName, Object id) {
        return new ResourceNotFoundException(
            String.format("%s을(를) 찾을 수 없습니다. (ID: %s)", resourceName, id)
        );
    }
}


