class RetryableError(Exception):
    """재시도 가능한 에러 (일시적 장애) - Airflow가 재시도"""
    pass


class PermanentError(Exception):
    """영구 실패 에러 (재시도 불가) - 다음 단계로 진행"""
    pass


class NetworkError(RetryableError):
    """네트워크 오류 (재시도 권장)"""
    pass


class TimeoutError(RetryableError):
    """타임아웃 오류 (재시도 권장)"""
    pass


class RateLimitError(RetryableError):
    """Rate Limit 오류 (재시도 필요)"""
    pass


class ValidationError(PermanentError):
    """데이터 검증 오류 (재시도 불가)"""
    pass


class ParseError(PermanentError):
    """파싱 오류 (재시도 불가)"""
    pass


class BlockedError(PermanentError):
    """차단 감지 오류 (재시도 불가)"""
    pass


class DatabaseError(RetryableError):
    """데이터베이스 오류 (재시도 권장)"""
    pass

class BillingLimitError(PermanentError):
    """OpenAI 결제 한도 도달 (재시도 불가)"""
    pass


class BatchFailedError(PermanentError):
    """OpenAI Batch API가 배치 전체를 실패 처리 (failed/expired/cancelled). 재시도 불가."""
    pass

