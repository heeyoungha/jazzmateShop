package shop.jazzmate.jazzmateshop;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import shop.jazzmate.jazzmateshop.common.exception.BusinessException;
import shop.jazzmate.jazzmateshop.common.exception.ResourceNotFoundException;

import jakarta.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.Map;
import java.util.Arrays;

/**
 * 전역 예외 처리 핸들러
 * 모든 예외를 중앙에서 처리하여 Controller의 예외 처리 로직 제거
 */
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    /**
     * @Valid 검증 실패 처리
     * 우선순위: 🥇 가장 먼저 체크되는 예외
     * DTO 유효성 검증 실패 시 400 Bad Request 반환
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidationException(
            MethodArgumentNotValidException ex, HttpServletRequest request) {
        String location = getControllerLocation(ex);
        log.warn("[{} {}] 유효성 검증 실패: {}", 
            request.getMethod(), request.getRequestURI(), ex.getMessage());
        log.debug("발생 위치: {}", location);
        
        String errorMessage = ex.getBindingResult()
                .getFieldErrors()
                .stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .findFirst()
                .orElse("유효성 검증에 실패했습니다.");

        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(createErrorResponse(errorMessage));
    }

    /**
     * 리소스 없음 예외 처리 (404)
     * 우선순위: 🥈 비즈니스 로직에서 명시적으로 던지는 예외
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<Map<String, Object>> handleResourceNotFoundException(
            ResourceNotFoundException ex, HttpServletRequest request) {
        String location = getControllerLocation(ex);
        log.warn("[{} {}] 리소스를 찾을 수 없음: {}", 
            request.getMethod(), request.getRequestURI(), ex.getMessage());
        log.debug("발생 위치: {}", location);
        
        return ResponseEntity
                .status(HttpStatus.NOT_FOUND)
                .body(createErrorResponse(ex.getMessage()));
    }

    /**
     * 비즈니스 규칙 위반 예외 처리 (400)
     * 우선순위: 🥈 비즈니스 로직 검증 실패
     */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Map<String, Object>> handleBusinessException(
            BusinessException ex, HttpServletRequest request) {
        String location = getControllerLocation(ex);
        log.warn("[{} {}] 비즈니스 규칙 위반: {}", 
            request.getMethod(), request.getRequestURI(), ex.getMessage());
        log.debug("발생 위치: {}", location);
        
        return ResponseEntity
                .status(HttpStatus.BAD_REQUEST)
                .body(createErrorResponse(ex.getMessage()));
    }

    /**
     * 그 외 모든 예외 처리 (500)
     * 우선순위: 🥉 예상하지 못한 예외
     * 참고: 이 핸들러가 마지막 방어선 역할
     */
    @ExceptionHandler(RuntimeException.class)
    public ResponseEntity<Map<String, Object>> handleRuntimeException(
            RuntimeException ex, HttpServletRequest request) {
        String location = getControllerLocation(ex);
        log.error("[{} {}] 예상하지 못한 서버 오류: {}", 
            request.getMethod(), request.getRequestURI(), ex.getMessage());
        log.error("발생 위치: {}", location, ex);
        
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(createErrorResponse("서버 내부 오류가 발생했습니다."));
    }

    /**
     * 최상위 예외 처리 (500)
     * 우선순위: 🪶 모든 예외의 마지막 방어선
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleException(
            Exception ex, HttpServletRequest request) {
        String location = getControllerLocation(ex);
        log.error("[{} {}] 알 수 없는 오류 발생: {}", 
            request.getMethod(), request.getRequestURI(), ex.getMessage());
        log.error("발생 위치: {}", location, ex);
        
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(createErrorResponse("서버 내부 오류가 발생했습니다."));
    }

    /**
     * 에러 응답 생성 헬퍼 메서드
     */
    private Map<String, Object> createErrorResponse(String message) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", false);
        response.put("message", message);
        return response;
    }

    /**
     * 예외가 발생한 컨트롤러 위치 정보 추출
     * StackTrace를 분석하여 Controller 클래스와 메서드 찾기
     */
    private String getControllerLocation(Exception ex) {
        StackTraceElement[] stackTrace = ex.getStackTrace();
        
        for (StackTraceElement element : stackTrace) {
            String className = element.getClassName();
            String methodName = element.getMethodName();
            
            // Controller 클래스 찾기 (Controller로 끝나는 클래스)
            if (className.contains("Controller") && 
                !className.contains("GlobalExceptionHandler")) {
                // 패키지 경로에서 클래스명만 추출
                String simpleClassName = className.substring(
                    className.lastIndexOf('.') + 1);
                return String.format("%s.%s()", simpleClassName, methodName);
            }
        }
        
        // Controller를 찾지 못한 경우 첫 번째 스택 정보 반환
        if (stackTrace.length > 0) {
            StackTraceElement first = stackTrace[0];
            String className = first.getClassName();
            String simpleClassName = className.substring(
                className.lastIndexOf('.') + 1);
            return String.format("%s.%s()", simpleClassName, first.getMethodName());
        }
        
        return "위치를 찾을 수 없음";
    }
}