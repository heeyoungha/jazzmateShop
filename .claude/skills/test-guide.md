---
name: test-guide
description: 모든 언어(Java, Python 등)에서 테스트 코드 작성 시 공통으로 지켜야 할 가이드. 행동 중심 테스트, 레이어별 테스트 원칙, 예외 처리 전략 등을 제공합니다.
---

# 테스트 코드 작성 가이드

## 🎯 핵심 원칙

- 문제가 생겼을 때 원인을 빠르게 좁힐 수 있는 테스트 코드
- 행동(Behavior) 중심 테스트: 내부 구현이 아닌 결과와 외부 인터페이스 검증
- 최소한의 테스트로 최대 신뢰도 확보

---

## ✅ 필수 테스트 항목 (3가지)

### 1. 비즈니스 핵심 로직
- 서비스의 주요 기능이 정상 동작하는지 검증
- CRUD의 각 작업 성공 케이스
- 경계값/Null/Optional.empty 등 대표 케이스 포함

### 2. 예외/실패 케이스
- 대표 케이스 1~2개만 유지 (중복 예외 테스트 제거)
- GlobalExceptionHandler 집중 테스트
- API별 리소스 없음(404)은 각 API 대표 케이스로 테스트 가능

### 3. 외부 의존성과 경계면
- DB, 외부 API, 메시지 큐 등
- Mock 활용하여 정상/실패 시나리오 검증

---

## 📊 테스트 종류별 전략

| 구분                  | 전략                 | 비고                            |
| ------------------- | ------------------ | ----------------------------- |
| 단위(Unit) 테스트        | 빠르고 작게, 로직 중심      | Mock 적극 사용, 내부 구현 의존 최소화      |
| 통합(Integration) 테스트 | 실제 DB/외부 API 연결 검증 | 핵심 시나리오만, TestContainers 추천   |
| E2E 테스트             | 사용자 시나리오 검증        | 최소화, Smoke Test 중심, CI/CD에 포함 |


---

## 🎚️ 레이어별 테스트 원칙

### Controller 테스트

- 목적: HTTP 인터페이스 검증
- 검증 항목
  - HTTP 상태 코드 (200, 400, 404, 500)
  - 요청/응답 JSON 구조
  - 핵심 필드 2~3개 검증 (id, trackName 등)
  - Service 호출 검증 (verify(times(1)))
- ❌ 피해야 할 항목
  - 모든 응답 필드 검증
  - 비즈니스 로직/데이터 변환
  - 내부 구현 세부사항

### Service 테스트

- 목적: 비즈니스 로직 및 데이터 처리 검증
- 검증 항목
  - 핵심 비즈니스 규칙
  - 트랜잭션 처리
  - 데이터 변환 및 계산
- 테스트 전략
  - 내부 상태보다 결과 검증
  - Mock 활용 최소화 (DB/Repository는 필요 시 Mock)

### Repository 테스트

- 목적: DB 쿼리 검증
- 검증 항목
  - CRUD 동작
  - 커스텀 쿼리 정확성
  - 페이징/정렬

---

## 🚨 예외 처리 테스트 전략

### GlobalExceptionHandler 중심

- Controller에서 try-catch 금지
- 모든 예외는 GlobalExceptionHandler에서 처리

| 예외 타입                           | HTTP 상태 | 처리 위치                  | 우선순위 |
| ------------------------------- | ------- | ---------------------- | ---- |
| MethodArgumentNotValidException | 400     | GlobalExceptionHandler | 🥇   |
| ResourceNotFoundException       | 404     | GlobalExceptionHandler | 🥈   |
| BusinessException               | 400     | GlobalExceptionHandler | 🥈   |
| RuntimeException                | 500     | GlobalExceptionHandler | 🥉   |
| Exception                       | 500     | GlobalExceptionHandler | 🪶   |

- 원칙
  - 대표 케이스 1개만 유지 (중복 제거)
  - API별 특화 메시지가 필요하면 각 API에서 테스트 가능
  - Controller에서 예외 처리 로직 제거

## 행동 중심 테스트

- 행동 = 결과 + 부수 효과
- Controller: HTTP 상태 + JSON 구조 + Service 호출
- Service: 결과와 상태 변화 검증
- Repository: 쿼리 결과 검증

```
// ✅ Controller 행동 중심 예
mockMvc.perform(post("/api/user-reviews")
.contentType(MediaType.APPLICATION_JSON)
.content(json))
.andExpect(status().isOk())
.andExpect(jsonPath("$.data.id").value(1));

verify(userReviewService, times(1))
.createUserReview(any(UserReviewRequest.class));
```

- ❌ 내부 호출/세부 구현 검증은 지양

## 유효성 검증 원칙

- DTO 레벨에서 @Valid로 처리
- Service에서 검증 로직 제거
- 테스트 시 Service Mock 불필요

```
// Controller
@PostMapping
public ResponseEntity<UserReviewResponse> create(
        @Valid @RequestBody UserReviewRequest request) {
    return ResponseEntity.ok(userReviewService.createUserReview(request));
}

```

## 📝 테스트 작성 체크리스트

**테스트 작성 전 자문**:
- [ ] 이 테스트가 깨지면 실제 버그를 의미하는가?
- [ ] 다른 테스트와 중복되지 않는가?
- [ ] 내부 구현이 아닌 행동을 테스트하는가?
- [ ] 테스트 이름만으로 무엇을 검증하는지 명확한가?
- [ ] 예외 테스트 대표 케이스만 유지했는가?
- [ ] Controller 테스트에서 불필요한 필드까지 검증하고 있지 않은가?
- [ ] HTTP 상태 코드 일관성을 유지했는가?
- [ ] 테스트 실행 속도가 팀 생산성에 영향을 주지 않는가?

### ✅ 통합 가능한 테스트 패턴

**같은 API의 분기 로직은 하나의 테스트에서 검증**
```java
// ❌ 나쁜 예 - 같은 API의 분기를 2개 테스트로 분리
@Test
void getUserReviews_WithoutUserId_ReturnsPublicReviews() { ... }
@Test
void getUserReviews_WithUserId_ReturnsUserReviews() { ... }

// ✅ 좋은 예 - 하나의 테스트에서 두 시나리오 모두 검증
@Test
void getUserReviews_WithAndWithoutUserId_ReturnsCorrectReviews() {
    // 시나리오 1: userId 없을 때
    // 시나리오 2: userId 있을 때
}
```

**통합 기준**:
- 같은 HTTP 메서드와 엔드포인트
- 파라미터 유무에 따른 분기 로직
- 비즈니스 로직이 동일하고 검증 목적이 같은 경우

---

## 💡 최종 요약

1. **핵심만 테스트**: 모든 경우를 다 테스트할 필요 없음
2. **중복 제거**:
   - 같은 타입의 예외 테스트는 1개만
   - **같은 HTTP 상태 코드를 반환하는 예외 테스트는 대표 케이스 1개만** (500 에러 테스트는 1개로 통합)
   - 같은 API의 분기 로직도 통합
3. **레이어 분리**: Controller는 HTTP만, Service는 로직만
4. **행동 중심**: 내부 구현이 아닌 결과를 검증
5. **일관성 유지**: 에러 처리 규칙을 명확히 정의
6. **유효성 검증**: `@Valid`를 DTO 레벨에서 처리, Service에서는 검증 로직 제거
7. **예외 처리**: GlobalExceptionHandler로 중앙 집중식 처리, Controller에서 try-catch 제거
8. **테스트 속도: 빠르고 신뢰성 있는 테스트 유지**

**목표: 적은 수의 테스트로 높은 신뢰도 확보, 유지보수 편의성 극대화**
