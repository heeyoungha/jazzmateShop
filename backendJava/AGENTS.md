# Java 백엔드 규칙

> 적용 범위: `backendJava/` 디렉터리의 Spring Boot 모듈
> 공통 규칙: [루트 AGENTS.md](../AGENTS.md)

---

## 설계 문서

> 구현 전 반드시 아래 문서를 먼저 읽는다.
> 문서 목적 및 사용 규칙: [docs/backendJava/design/README.md](../docs/backendJava/design/README.md)

| 문서 | 내용 | 언제 확인할지 |
|------|------|---------------|
| [SDD.md](../docs/backendJava/design/SDD.md) | 레이어 책임 경계, 플로우별 설계, 테스트 시나리오, 테스트 전략 원칙 | 기능 구현 전, 플로우 설계 변경 시 |
| [API_SPEC.md](../docs/backendJava/design/API_SPEC.md) | 전체 엔드포인트 요청/응답 명세 | API 추가/변경 시 |
| [DB_SPEC.md](../docs/backendJava/design/DB_SPEC.md) | DB 테이블·Entity·DTO·Enum 필드 명세 | DB/Entity/DTO 추가·수정 시 |

---

## 설계 기준 (ADR)

구현 변경 시 아래 ADR을 우선 확인한다.

| ADR | 주제 | 언제 확인할지 |
|---|---|---|
| [ADR-B001](../docs/backendJava/adr/001-test-strategy.md) | 테스트 전략 | 테스트 레이어 분리, 도구 선택, 검증 방식 변경 시 |
| [ADR-B002](../docs/backendJava/adr/002-backend-design.md) | 백엔드 설계 결정 | DTO 패턴, recommendationStatus 전이 정책 변경 시 |

---

## 코딩 컨벤션

### Best Practice 규칙 (위반 시 반려)

| # | 규칙 | 금지 | 권장 |
|---|------|------|------|
| 1 | Entity Annotation | `@Data` | `@Getter` + 필요한 곳만 `@Setter` |
| 2 | Entity equals/hashCode | 기본 `@EqualsAndHashCode` (전체 필드) | `@EqualsAndHashCode(onlyExplicitlyIncluded=true)` + `@Id`에 `@EqualsAndHashCode.Include`; persist 전 Entity를 hash collection key로 사용 금지 |
| 3 | Entity 기본 생성자 | `public` 기본 생성자 | `@NoArgsConstructor(access = AccessLevel.PROTECTED)` |
| 4 | Entity 상태 변경 | 상태 전이용 setter 직접 노출 | 의미 있는 도메인 메서드 |
| 5 | Controller 예외 처리 | try-catch | 예외 전파 → `GlobalExceptionHandler` |
| 6 | Service 예외 처리 | `throw new RuntimeException(e)` | 도메인/애플리케이션 예외로 변환하고 원인 예외 보존 |
| 7 | 페이징 | `findAll()` 후 `subList()` | `Pageable` Repository 전달 |
| 8 | HTTP 클라이언트 | Service 내 직접 생성 | 외부 HTTP 호출은 전용 Client 컴포넌트로 분리 (`AiRecommendationClient` 등) |
| 9 | 타임스탬프 | `LocalDateTime.now()` 수동 | `@CreationTimestamp` / `@UpdateTimestamp` 또는 JPA Auditing |
| 10 | DTO 변환 | Service의 `convertToXxx()` 메서드, Response DTO의 Entity 직접 노출 | Response DTO 내 `static from(entity)` 팩토리 메서드 + nested Response DTO |
| 11 | 요청 바인딩 | Controller에서 Entity 직접 `@RequestBody` | Create/Update Request DTO |
| 12 | 비동기 시작 시점 | 트랜잭션 내부에서 외부 API 직접 호출 | 도메인 이벤트 + `@TransactionalEventListener(AFTER_COMMIT)`; 실패 시 상태 전이 정책 명시 |
| 13 | 추천 완료 알림 | 단건/단계별 콜백 | batch 저장 커밋 후 SSE `recommendation-ready` 1회 emit |
| 14 | 조회 트랜잭션 | 기본값 생략 | `@Transactional(readOnly = true)` 명시 |
| 15 | 테스트 우선순위 | `@SpringBootTest` 남용 | `@WebMvcTest`, `@DataJpaTest`, Mockito 단위 테스트 우선; context load/전체 플로우 smoke test는 최소 허용 |
| 16 | Enum 저장 | `@Enumerated` 생략 또는 `ORDINAL` | `@Enumerated(EnumType.STRING)` |
| 17 | Entity 생성 패턴 | public all-args 생성자 | `@Builder` + `@AllArgsConstructor(access = AccessLevel.PRIVATE)` |

### 응답 형식

```
생성 성공:   ApiResponse<T>  { success:true,  message:"...", data: T }
조회 단건:   DTO 직접 반환
조회 목록:   List<DTO> 또는 Page<DTO> 직접 반환
FastAPI 콜백 응답: ResponseEntity<Void>
에러:        ErrorResponse   { success:false, message:"..." }
```
