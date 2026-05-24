# ADR-BJ001: 테스트 전략

## Context

JazzmateShop 백엔드는 TDD 방식으로 구현한다. 테스트 코드를 먼저 작성하고, 이를 통과하는 구현체를 작성한다.
테스트 레이어 분리, 도구 선택, 검증 방식에 대한 결정이 필요했다.

---

## Decision 1: 테스트 레이어 분리 원칙

의존 방향(하위 → 상위)을 따라 레이어를 분리한다.
실패 시 어느 레이어 문제인지 즉시 파악할 수 있다.

```
Phase 1: 순수 단위        DtoFactoryTest
Phase 2: Repository       UserReviewRepositoryTest (@DataJpaTest, H2)
Phase 3: Service 단위     AlbumServiceTest → RecommendAlbumServiceTest → UserReviewServiceTest
Phase 4: EventListener    RecommendationEventListenerTest
Phase 5: Controller 슬라이스  GlobalExceptionHandlerTest → UserReviewControllerTest
Phase 6: 통합 테스트      RecommendationFlowIntegrationTest (@SpringBootTest, Awaitility)
```

### 레이어별 도구 선택 이유

| 레이어 | 도구 | 검증 대상 |
|--------|------|-----------|
| 순수 단위 | JUnit5 only | Spring 컨텍스트 불필요, 가장 빠름 |
| Repository | `@DataJpaTest` + H2 | JPA 쿼리/매핑만 검증, 전체 컨텍스트 불필요 |
| Service | Mockito | 비즈니스 로직, 상태 전이, 이벤트 발행 |
| Controller `@WebMvcTest` | MockMvc | 예외 경로만 — `@Valid` → 400, 예외 → 404/500 포맷 |
| 통합 | `@SpringBootTest` | 성공 경로 전체 플로우, AFTER_COMMIT + @Async 타이밍 |
| E2E | Playwright | 프론트엔드 UI 동작, 사용자 관점 시나리오 |

### Controller 테스트 범위 결정 근거

`@WebMvcTest`에서 Service를 mock하면 성공 경로 검증은 "내가 넣은 stub 값을 내가 확인하는" 구조가 된다.
실제 비즈니스 로직은 검증되지 않으므로, **Controller 슬라이스 테스트는 예외 경로(400, 404)에만 집중**한다.

성공 경로는 실제 클래스가 연결된 `@SpringBootTest` 통합 테스트에서 검증한다.

---

## Decision 2: 상태 기반 테스트를 행위 기반보다 우선한다

상태 조회 테스트에서는 Repository 호출 여부 같은 행위 검증만으로는 부족하다.
프론트 polling 분기 계약이 깨지지 않도록 응답 상태와 추천 목록을 직접 검증한다.

```java
verify(eventPublisher, never()).publishEvent(any());
assertThat(result.getRecommendationStatus()).isEqualTo(RecommendationStatus.PENDING);
assertThat(result.getRecommendations()).isEmpty();
```

상태 기반 검증은 `PENDING`, `COMPLETED`, `FAILED` 분기와 retry 정책을 명확히 보호한다.

---

## Decision 3: 예외 처리 테스트 이중 검증 전략

### Context

`GlobalExceptionHandler`가 처리하는 예외(400, 404, 500)를 각 Controller 테스트에서도 검증하면 중복이 발생한다.
중복을 제거하면 `@Import(GlobalExceptionHandler.class)` 누락 같은 설정 실수를 특정 Controller 테스트에서 잡지 못한다.

### Decision

중복이더라도 두 계층에서 모두 검증한다. 단, 검증 목적을 명확히 분리한다.

| 테스트 클래스 | 목적 | 검증 내용 |
|---|---|---|
| `GlobalExceptionHandlerTest` | 포맷 검증 | `success=false`, `message` 내용, 상태코드 매핑이 올바른가 |
| 각 `*ControllerTest` | QA 관점 | 해당 엔드포인트에서 실제로 예외 응답이 나오는가 (설정 실수 탐지) |

### 근거

- `GlobalExceptionHandler`가 등록되지 않은 Controller는 예외 응답 형식이 달라질 수 있다
- QA 관점에서는 "이 엔드포인트가 잘못된 입력에 올바르게 응답하는가"를 엔드포인트별로 보장해야 한다
- 중복 비용보다 설정 실수 조기 발견의 이점이 크다

---

## Consequences

- 테스트 실행 순서를 Phase 순서대로 유지하면 실패 원인 추적이 빠르다
- `DtoFactoryTest`에서 검증한 팩토리는 다른 테스트에서 중복 검증 제거
- 예외 처리 테스트는 의도적으로 중복 허용 — `GlobalExceptionHandlerTest`(포맷) + 각 Controller 테스트(QA)
- Controller 성공 경로 테스트는 작성하지 않음 — `@SpringBootTest` 통합 테스트 또는 Playwright E2E에서 검증
