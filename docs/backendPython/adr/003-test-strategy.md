# ADR-BP003: Python 백엔드 테스트 전략

## Context

FastAPI 추천 서버는 외부 의존성이 많은 비동기 처리 흐름을 가진다.

- OpenAI Embeddings API
- OpenAI Chat API
- Supabase/PostgreSQL
- Spring Boot 콜백 API

실제 네트워크를 기본 테스트에 포함하면 테스트가 느리고 불안정하며 비용이 발생할 수 있다.

---

## Decision 1: 테스트 레이어를 분리한다

테스트는 아래 순서로 작성한다.

```text
Phase 1: Schema/DTO 단위 테스트
Phase 2: 순수 로직 테스트
Phase 3: Service 단위 테스트
Phase 4: Client/Repository mock 테스트
Phase 5: Router 테스트
Phase 6: 통합 플로우 테스트
```

| Phase | 테스트 범위 | 검증 대상 |
|---|---|---|
| 1 | Schema/DTO | API 필드명, 필수값, 타입 검증 |
| 2 | 순수 로직 | 점수 정규화, TOP K 제한, payload 변환 |
| 3 | Service | 추천 처리 유스케이스 조합 |
| 4 | Client/Repository | OpenAI, Supabase, Spring 통신 격리 검증 |
| 5 | Router | HTTP 상태코드와 background task 등록 |
| 6 | 통합 플로우 | FastAPI 내부 성공/실패 흐름 연결 검증 |

---

## Decision 2: 외부 네트워크는 기본 테스트에서 호출하지 않는다

기본 테스트에서는 OpenAI, Supabase, Spring Boot를 fake/mock으로 대체한다.

권장 도구:

- `pytest`
- `pytest-asyncio`
- `respx`
- `httpx.MockTransport`
- OpenAI SDK client wrapper mock

실제 네트워크 통합 테스트가 필요하면 `integration` marker를 붙이고 기본 테스트 실행에서 제외한다.

---

## Decision 3: Router 테스트와 처리 완료 테스트를 분리한다

`POST /recommend/by-review`는 정상 요청에서 `202 Accepted`를 즉시 반환해야 한다.

따라서 Router 테스트는 다음을 검증한다.

- 요청 검증
- HTTP 202
- background task 등록 또는 service 위임

추천 처리 완료 여부는 Service/통합 테스트에서 별도로 검증한다.

---

## Decision 4: Inbound snake_case와 outbound callback camelCase를 분리해 검증한다

FastAPI의 외부 경계는 두 방향이다.

| 방향 | API | 필드 컨벤션 | 비고 |
|---|---|---|---|
| Spring Boot → FastAPI | `POST /recommend/by-review` | snake_case | `review_id`, `review_content` |
| FastAPI → Spring Boot | `POST /api/user-reviews/{reviewId}/recommendations` | camelCase | `status`, `albumId`, `recommendationScore`, `recommendationReason`, `errorCode`, `message` |

`POST /recommend/by-review`의 `202 Accepted` 응답은 body가 없거나 처리 시작 확인용이어야 한다.
FastAPI가 브라우저나 Spring에 추천 결과 JSON을 직접 응답 body로 반환하지 않는다.

따라서 테스트는 다음을 분리해서 검증한다.

- inbound request DTO는 `review_id`, `review_content` snake_case를 받는다.
- 내부 모델은 Python 관례에 따라 snake_case를 사용한다.
- outbound Spring callback JSON만 Spring DTO 계약에 맞춰 직렬화한다.
- 성공 콜백은 `status=COMPLETED`와 `recommendations[]`를 포함한다.
- 실패 콜백은 `status=FAILED`, `errorCode`, `message`, 빈 `recommendations[]`를 포함한다.

Spring Boot 콜백 payload는 프론트 최종 화면까지 이어지는 핵심 계약이므로 다음 필드명을 그대로 검증한다.

- `albumId`
- `recommendationScore`
- `recommendationReason`
- `errorCode`
- `message`

---

## Decision 5: 추천 사유 생성은 성공/실패/fallback을 모두 검증한다

추천 사유 생성 계층은 LLM 호출 품질과 추천 완료율에 직접 영향을 준다.

테스트는 다음 분기를 분리해서 검증한다.

- OpenAI Chat client가 설정값으로 초기화되는가
- 후보별 reason이 원래 `album_id`와 매칭되는가
- 여러 후보를 비동기로 병렬 처리할 수 있는가
- LLM 실패 또는 빈 응답에서 fallback 사유를 반환하는가
- fallback 사유가 완전한 한국어 문장이고 비어 있지 않은가

---

## Decision 6: 테스트 함수명은 영문 snake_case를 사용한다

`pytest`는 한글 테스트 함수명을 기술적으로 허용하지만, 이 프로젝트에서는 테스트 함수명을 영문 `snake_case`로 작성한다.

예:

```python
def test_post_by_review_valid_request_returns_202():
    """유효한 추천 요청이면 HTTP 202를 반환한다."""
```

### Rationale

- Java/Frontend 문서의 테스트 메서드명도 영문 식별자 패턴을 사용한다.
- CI, coverage, pytest plugin, IDE, 터미널 환경에서 인코딩 이슈를 피할 수 있다.
- 실패 로그에서 안정적으로 검색 가능한 식별자로 쓰기 쉽다.
- Python 코드 컨벤션과 맞다.

한글은 테스트 시나리오 설명, docstring, assertion message에 사용한다.

---

## Consequences

- 비용과 네트워크 상태에 의존하지 않는 빠른 테스트를 유지한다.
- 실패 시 Router, Service, Client/Repository 중 어느 레이어 문제인지 추적하기 쉽다.
- 비동기 API 응답 계약과 백그라운드 추천 처리 계약을 혼동하지 않는다.
- 테스트 함수명은 영문으로 유지하되, 문서와 docstring은 한글 설명을 허용한다.
- 상세 테스트 케이스는 [flows/](../flows/)의 각 플로우 문서에 둔다.
