# Java 백엔드 규칙

> 적용 범위: `backendJava/` 디렉터리의 Spring Boot 모듈
> 공통 규칙: [루트 AGENTS.md](../AGENTS.md)

---

## 설계 문서

| 문서 | 내용 | 언제 확인할지 |
|------|------|---------------|
| [SDD.md](../docs/backendJava/design/SDD.md) | 레이어 책임 경계, 플로우 문서 인덱스, 공통 설계 원칙 | 기능 구현 전, 공통 설계 변경 시 |
| [flows/](../docs/backendJava/design/flows/) | 프론트 페이지별 사용자 플로우, 테스트 시나리오, 관련 구성요소 | 플로우 구현 전, 플로우 설계 변경 시 |
| [API_SPEC.md](../docs/backendJava/design/API_SPEC.md) | 전체 엔드포인트 요청/응답 명세 | API 추가/변경 시 |
| [DB_SPEC.md](../docs/backendJava/design/DB_SPEC.md) | DB 테이블·Entity·DTO·Enum 필드 명세 | DB/Entity/DTO 추가·수정 시 |

---

## 설계 기준 (ADR)

구현 변경 시 아래 ADR을 우선 확인한다.

| ADR | 주제 | 언제 확인할지 |
|---|---|---|
| [ADR-B001](../docs/backendJava/adr/001-test-strategy.md) | 테스트 전략 | 테스트 레이어 분리, 도구 선택, 검증 방식 변경 시 |
| [ADR-B002](../docs/backendJava/adr/002-backend-design.md) | 백엔드 설계 결정 | DTO 패턴, recommendationStatus 전이 정책 변경 시 |
| [ADR-B003](../docs/backendJava/adr/003-realtime-notification-strategy.md) | AI 추천 상태 확인 방식 | polling, SSE, WebSocket, WebFlux, 브로커 기반 상태 확인/알림 구조 변경 시 |
| [Polling → SSE 전환 노트](../docs/backendJava/migration-notes/polling-to-sse.md) | 전환 가이드 | polling에서 SSE로 구조 변경 시 |

---

## 코딩 컨벤션

### Best Practice 규칙 (위반 시 반려)

#### 작업별 빠른 참조

| 작업 | 먼저 볼 섹션 |
|------|--------------|
| Entity / Enum / Repository 수정 | Entity / Persistence |
| API 요청·응답 / Controller 수정 | DTO / Controller |
| Service / 트랜잭션 / 상태 전이 수정 | Service / Transaction |
| FastAPI 호출 / polling / 비동기 이벤트 수정 | Integration / Async |
| 테스트 추가·수정 | Test |

#### Entity / Persistence

> 참고 시점: Entity, Enum, Repository 쿼리, DB 매핑을 추가·수정할 때

| 규칙 | 금지 | 권장 |
|------|------|------|
| Entity Annotation | `@Data` | `@Getter` + 필요한 곳만 `@Setter` |
| Entity equals/hashCode | 기본 `@EqualsAndHashCode` (전체 필드) | `@EqualsAndHashCode(onlyExplicitlyIncluded=true)` + `@Id`에 `@EqualsAndHashCode.Include`; persist 전 Entity를 hash collection key로 사용 금지 |
| Entity 기본 생성자 | `public` 기본 생성자 | `@NoArgsConstructor(access = AccessLevel.PROTECTED)` |
| Entity 상태 변경 | 상태 전이용 setter 직접 노출 | 의미 있는 도메인 메서드 |
| Entity 생성 패턴 | public all-args 생성자 | `@Builder` + `@AllArgsConstructor(access = AccessLevel.PRIVATE)` |
| Enum 저장 | `@Enumerated` 생략 또는 `ORDINAL` | `@Enumerated(EnumType.STRING)` |
| 타임스탬프 | `LocalDateTime.now()` 수동 | `@CreationTimestamp` / `@UpdateTimestamp` 또는 JPA Auditing |
| 페이징 | `findAll()` 후 `subList()` | `Pageable` Repository 전달 |

#### DTO / Controller

> 참고 시점: API 요청/응답, Controller, DTO를 추가·수정할 때

| 규칙 | 금지 | 권장 |
|------|------|------|
| 요청 바인딩 | Controller에서 Entity 직접 `@RequestBody` | Create/Update Request DTO |
| DTO 변환 | Service의 `convertToXxx()` 메서드, Response DTO의 Entity 직접 노출 | Response DTO 내 `static from(entity)` 팩토리 메서드 + nested Response DTO |
| Controller 예외 처리 | try-catch | 예외 전파 → `GlobalExceptionHandler` |

#### Service / Transaction

> 참고 시점: Service 로직, 트랜잭션 경계, 상태 변경 흐름을 구현할 때

| 규칙 | 금지 | 권장 |
|------|------|------|
| Service 예외 처리 | `throw new RuntimeException(e)` | 도메인/애플리케이션 예외로 변환하고 원인 예외 보존 |
| 조회 트랜잭션 | 기본값 생략 | `@Transactional(readOnly = true)` 명시 |
| 조회 메서드 책임 | `readOnly=true` 조회 메서드에서 Entity 상태 변경 | 상태 변경은 쓰기 트랜잭션 메서드로 분리 |
| 추천 결과 저장 | 추천 앨범을 Service에서 `save()` 반복 호출 | FastAPI 콜백으로 받은 추천 결과는 `saveAll()`로 하나의 트랜잭션에서 저장 |
| 추천 재시도 | GET 조회 시 FAILED 상태에서 이벤트 자동 재발행 | 명시적 retry 엔드포인트에서만 `FAILED → PENDING` 전이 후 이벤트 재발행 |

#### Integration / Async

> 참고 시점: 외부 API 호출, 비동기 이벤트, polling 상태 조회를 구현할 때

| 규칙 | 금지 | 권장 |
|------|------|------|
| HTTP 클라이언트 | Service 내 직접 생성 | 외부 HTTP 호출은 전용 Client 컴포넌트로 분리 (`AiRecommendationClient` 등) |
| 비동기 시작 시점 | 트랜잭션 내부에서 외부 API 직접 호출 | 도메인 이벤트 + `@TransactionalEventListener(AFTER_COMMIT)`; 실패 시 상태 전이 정책 명시 |
| 추천 상태 확인 | GET 조회 시 상태 변경 또는 자동 재발행 | `PENDING`은 polling 응답만 반환, `FAILED` 재시도는 명시적 retry 엔드포인트에서만 처리 |

#### Test

> 참고 시점: 테스트를 추가·수정하거나 테스트 전략을 바꿀 때

| 규칙 | 금지 | 권장 |
|------|------|------|
| 테스트 우선순위 | `@SpringBootTest` 남용 | `@WebMvcTest`, `@DataJpaTest`, Mockito 단위 테스트 우선; context load/전체 플로우 smoke test는 최소 허용 |

### 응답 형식

```
생성 성공:   ApiResponse<T>  { success:true,  message:"...", data: T }
조회 단건:   DTO 직접 반환
조회 목록:   List<DTO> 또는 Page<DTO> 직접 반환
FastAPI 콜백 응답: ResponseEntity<Void>
에러:        ErrorResponse   { success:false, message:"..." }
```
