# ADR-BJ002: 백엔드 설계 결정

## Context

JazzmateShop 백엔드 구현 과정에서 DTO 생성 패턴, AI 추천 상태 관리 방식, 추천 결과 저장 방식, 조회 트랜잭션 정책에 대한 결정이 필요했다.

---

## Decision 1: Request는 Builder, Response는 from() 팩토리 사용

DTO는 역할에 따라 두 종류로 나뉜다.

| 종류 | 방향 | 역할 |
|------|------|------|
| Request DTO | 외부 → 내부 | 입력 데이터 전달 |
| Response DTO | 내부 → 외부 | 응답 데이터 표현 |

**Request DTO는 Builder 중심으로 사용한다**

- Request → Entity 변환은 단순 데이터 복사가 아니라 도메인 객체를 생성하는 과정이다.
- 비밀번호 암호화, 기본값 설정, 도메인 규칙 적용 등의 로직이 포함될 수 있으므로
- Service에서 Builder를 사용해 객체 생성 의도를 명확하게 드러낸다.

**Response DTO는 from() 팩토리를 사용한다**

- Entity → Response DTO는 단순 매핑 작업이다.
- `UserResponse.from(user)`처럼 변환 로직을 DTO 내부에 집중시켜 Service 책임을 단순화한다.
- 따라서 Service에 `convertToXxx()` 같은 변환 메서드를 두지 않는다 — DTO가 자신의 생성 책임을 직접 갖는다.

### 테스트 위치

- `@NotBlank` 등 Request DTO 검증 → `@WebMvcTest` Controller 슬라이스 테스트
- Response DTO `from()` 팩토리 필드 매핑 검증 → `DtoFactoryTest` 집중, 다른 테스트에서 중복 검증 금지

---

## Decision 2: recommendationStatus로 AI 추천 처리 상태 관리

### Context

`getUserReview` 조회 시 추천 앨범이 없는 경우 두 가지 가능성이 있다:

1. AI가 아직 처리 중 (정상 — 재발행 불필요)
2. AI 처리 실패 (비정상 — 재발행 필요)

이 둘을 구분하지 않으면 조회할 때마다 이벤트가 중복 발행되거나, 실패한 경우를 영원히 방치하게 된다.

### Decision

`UserReview` 엔티티에 `RecommendationStatus` 열거형 필드를 추가하여 AI 추천 처리 상태를 관리한다.

| 상태 | 의미 | 다음 전이 |
|------|------|-----------|
| `PENDING` | 생성 직후, 이벤트 발행됨, AI 처리 중 | → COMPLETED / FAILED |
| `COMPLETED` | AI 추천 앨범 저장 완료 | 종료 |
| `FAILED` | AI 처리 실패 | → PENDING (재시도 시) |


1. `createUserReview`
   - 저장 (status=PENDING) + RecommendationRequestEvent 발행
2. `getUserReview` 조회 (`@Transactional(readOnly=true)`)
   - PENDING   → 빈 recommendations, 이벤트 재발행 안 함
   - COMPLETED → 추천 앨범 포함 응답
   - FAILED    → 빈 recommendations 반환만 (이벤트 재발행 안 함)
3. `retryRecommendation` (`POST /{id}/retry`)
   - FAILED 상태에서만 호출 — status=PENDING 전이 + RecommendationRequestEvent 재발행
   - GET 조회 시 자동 재발행하지 않는 이유: 페이지 새로고침마다 무한 재시도 루프 방지
4. AI 처리
   - 완료 → FastAPI가 `POST /{reviewId}/recommendations`에 `status=COMPLETED` 콜백 → `saveAll()` 일괄 저장 → status=COMPLETED
   - 실패 → FastAPI가 같은 콜백 API에 `status=FAILED` 콜백 → 추천 저장 없이 status=FAILED
   - FastAPI 호출 자체 실패 또는 콜백 미수신 → Spring 실패 정책에 따라 status=FAILED

---

## Decision 3: COMPLETED 추천 결과는 saveAll()로 하나의 트랜잭션에서 일괄 저장

### Context

FastAPI는 추천 처리 결과를 하나의 콜백 요청으로 Spring Boot에 전달한다.
`status=COMPLETED`일 때는 추천 앨범 N건을 함께 전달하고, `status=FAILED`일 때는 추천 저장 없이 상태만 FAILED로 전이한다.
각 추천 결과를 Service에서 개별 `save()` 호출로 저장하면 요청 단위의 저장 의도가 분산되고, 중복 실패 처리도 흐려진다.

### Decision

`status=COMPLETED` 콜백의 추천 결과는 `RecommendAlbum` 리스트로 변환한 뒤 `saveAll()`로 저장한다.
이 저장 작업은 하나의 `@Transactional` 메서드 안에서 처리한다.

- 추천 앨범 N건이 하나의 콜백으로 도착하므로 `saveAll()`로 하나의 트랜잭션에서 일괄 저장한다.
- `status=FAILED` 콜백은 `saveAll()`을 호출하지 않고 감상문 상태만 `FAILED`로 전이한다.
- 현재 구현은 단일 SQL insert를 보장하지 않으며, 추천 건수가 커져 병목이 확인되면 JDBC batching 또는 bulk insert를 검토한다.
- 중복 발생(`UNIQUE(user_review_id, album_id)` 위반 — 동일 감상문에 같은 앨범이 재저장되는 경우) 시 전체 실패 — FastAPI 재시도에 위임한다.

---

## Decision 4: 조회 Service는 readOnly 트랜잭션을 명시

### Context

`getUserReview` 같은 조회 Service는 Entity 상태를 변경하지 않는다.
쓰기 트랜잭션과 구분하지 않으면 메서드 의도가 불명확하고, JPA flush/dirty checking 비용도 불필요하게 발생할 수 있다.

### Decision

조회 전용 Service 메서드는 `@Transactional(readOnly=true)`를 명시한다.

- 조회 전용 의도를 코드에 드러낸다.
- JPA flush 비용을 줄인다.
- 단, `readOnly=true`가 모든 환경에서 쓰기 차단을 절대 보장하는 것은 아니므로 상태 변경 로직은 조회 메서드에 두지 않는다.

---

## Decision 5: 에러 처리 전략

### Context

예외 처리를 각 레이어에서 개별적으로 하면 응답 형식이 일관되지 않고, try-catch가 비즈니스 로직과 섞인다.

### Decision

1. Controller / Service에서 try-catch 금지 — 예외는 `GlobalExceptionHandler`로 전파
2. `orElseThrow()` 내부에서 `ResourceNotFoundException` 직접 생성
3. 외부 API 실패처럼 메인 트랜잭션과 분리해야 하는 예외만 Client 내부에서 처리

---

## Consequences

**Decision 1**
- Service에 `convertToXxx()` 메서드 금지 — 위반 시 테스트 실패
- Request DTO에 `from()` 팩토리 추가 금지 — 역할 혼란 방지

**Decision 2**
- GET 조회 시 FAILED 상태에서 이벤트 자동 재발행 금지 — 페이지 새로고침마다 무한 재시도 루프 방지
- 재시도는 반드시 `POST /{id}/retry` 명시적 엔드포인트를 통해서만 가능
- `retryRecommendation`은 FAILED 상태 전용 — PENDING/COMPLETED 상태에서의 호출 동작은 미정의

**Decision 3**
- `COMPLETED` 추천 저장은 `saveAll()`로 하나의 트랜잭션에서 일괄 처리
- `FAILED` 콜백은 추천 저장 없이 상태만 전이
- 현재 구현은 단일 SQL insert를 보장하지 않음 — 추천 건수가 커져 병목이 확인되면 JDBC batching 또는 bulk insert 검토
- 중복 발생 시 전체 저장 실패 — FastAPI 재시도에 위임

**Decision 4**
- 조회 Service에는 `@Transactional(readOnly=true)` 명시
- 조회 메서드에는 Entity 상태 변경 로직을 두지 않음

**Decision 5**
- Controller / Service에 try-catch 금지 — 위반 시 `GlobalExceptionHandler` 우회 가능성
- Client 내부 catch는 메인 트랜잭션 보호 목적으로만 허용
