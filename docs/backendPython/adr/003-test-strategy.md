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

| 레이어 | 검증 대상 | 검증하지 않는 것 |
|---|---|---|
| Schema/DTO | API 필드명, 필수값, 타입, 값 범위, trim·공백 | HTTP 상태코드 |
| 순수 로직 | 점수 정규화, TOP K 제한, payload 변환 | - |
| Service | 추천 처리 유스케이스 조합 | HTTP 계층, 외부 네트워크 |
| Client/Repository | OpenAI, Supabase, Spring 통신 격리 검증 | 비즈니스 로직 |
| Router | HTTP 상태코드와 background task 등록 | 입력값 유효성 세부 규칙 |
| 통합 플로우 | FastAPI 내부 성공/실패 흐름 연결 검증 | - |

---

### 레이어별 핵심 질문과 테스트 파일

| 레이어 | 핵심 질문 |
|---|---|
| Schema/DTO | 입력 필드명·타입·필수값이 계약대로인가? | 
| 순수 로직 | 점수 계산·정렬·변환 결과가 정확한가? | 
| Service | 유스케이스 흐름(임베딩→검색→이유 생성→콜백)이 올바르게 조합되는가? |
| Client/Repository | 외부 API 호출 시 올바른 payload를 보내고 응답을 올바르게 파싱하는가? |
| Router | HTTP 요청이 들어왔을 때 올바른 상태코드를 반환하고 background task를 등록하는가? |
| Dependency wiring | FastAPI provider가 app-scoped 리소스를 실제 협력 객체에 주입하고, 누락 시 명확히 실패하는가? |
| 통합 플로우 | HTTP 입력값이 손실 없이 Service까지 올바르게 전달되는가? | 

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

## Decision 2-1: 운영 dependency wiring을 별도 테스트로 고정한다

OpenAI, Supabase, Spring Boot는 기본 테스트에서 fake/mock으로 대체하지만, production dependency graph 자체는 테스트해야 한다.
특히 DB client, OpenAI async client, Spring 콜백용 HTTP client 같은 app-scoped 필수 리소스가 누락된 상태로 `RecommendationService`, Repository, Client wrapper가 조립되면 안 된다.

검증 기준:

- `AlbumEmbeddingRepository(database=None)`은 정상 생성 경로가 아니며, 설정 누락을 설명하는 명확한 예외를 발생시킨다.
- `EmbeddingService(openai_client=None)`, `RecommendationReasonService(openai_client=None)`, `SpringCallbackClient(http_client=None)`은 운영 조립 경로가 아니다.
- `get_recommendation_service(request)`는 `request.app.state`의 DB client, OpenAI client, HTTP client를 각 협력 객체에 주입한다.
- `request.app.state`에 필수 app-scoped 리소스가 없거나 `None`이면 dependency provider가 명확한 설정 오류를 발생시킨다.
- lifespan 테스트는 app startup에서 필수 client가 `app.state`에 등록되고 shutdown에서 닫히는지 fake close hook으로 검증한다.
- Service 단위 테스트는 fake repository를 생성자에 직접 주입한다. Service 기본 생성자가 운영용 Repository를 `database=None`으로 만드는 경로에 의존하지 않는다.
- Router 테스트는 `app.dependency_overrides`로 service provider를 교체해 HTTP 계약만 검증하고, dependency wiring 테스트와 책임을 섞지 않는다.

권장 테스트 파일:

| 파일 | 검증 대상 |
|---|---|
| `tests/unit/test_album_embedding_repository.py` | Repository 생성자에서 필수 DB client 누락 방지, View 조회 계약 |
| `tests/unit/test_dependencies.py` | FastAPI dependency provider가 app state 리소스를 Service/Repository/Client wrapper에 주입 |
| `tests/unit/test_lifespan.py` | FastAPI lifespan이 app-scoped 리소스를 생성하고 종료 시 닫는지 검증 |
| `tests/integration/test_recommendation_flow.py` | endpoint override 기반 HTTP 요청 → background task 위임 흐름 |

예시 시나리오:

| 시나리오 | 기댓값 |
|---|---|
| Repository에 DB client 없음 | 설정 누락 예외 발생 |
| Client wrapper에 OpenAI/HTTP client 없음 | 설정 누락 예외 발생 |
| app state에 필수 리소스 있음 | provider가 해당 리소스로 협력 객체를 조립 |
| app state에 필수 리소스 없음 | provider가 설정 누락 예외 발생 |
| lifespan shutdown 실행 | 닫아야 하는 client의 close hook 호출 |
| Service 테스트에서 fake repository 주입 | 실제 DB client 없이 유스케이스 분기 검증 가능 |

이 테스트는 실제 Supabase 네트워크 연결을 하지 않는다.
fake DB/OpenAI/HTTP client를 사용하되, fake가 production wiring 위치에 주입되고 종료 hook이 호출되는지 검증한다.

---

## Decision 3: Inbound snake_case와 outbound callback camelCase를 분리해 검증한다


FastAPI의 외부 경계는 두 방향이다.

| 방향 | API | 필드 컨벤션 | 비고 |
|---|---|---|---|
| Spring Boot → FastAPI | 추천 시작 API | snake_case | `review_id`, `review_content` |
| FastAPI → Spring Boot | `POST /api/user-reviews/{reviewId}/recommendations` | camelCase | `status`, `albumId`, `recommendationScore`, `recommendationReason`, `errorCode`, `message` |

추천 시작 API의 `202 Accepted` 응답은 body가 없거나 처리 시작 확인용이어야 한다.
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

## Decision 4: 테스트 함수명은 영문 snake_case를 사용한다

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

## Decision 5: pytest fixture와 fake 작성 관례를 고정한다

pytest 테스트는 다음 기준으로 작성한다.

| 항목 | 기준 |
|---|---|
| `conftest.py` | pytest가 자동 주입할 fixture만 둔다. 테스트 데이터 상수나 helper를 직접 import하는 용도로 쓰지 않는다. |
| 공유 테스트 데이터 | `tests/fixtures.py` 같은 일반 모듈에 둔다. 테스트에서는 `from tests.fixtures import ...`로 명시적으로 가져온다. |
| 외부 의존성 fake | 테스트 파일 안에 작게 둔다. 여러 파일에서 공유될 정도로 커지면 `tests/fakes.py`로 분리한다. |
| FastAPI `TestClient` | 테스트마다 직접 생성하지 않고 `client` fixture를 사용한다. |
| HTTP mock | `httpx.MockTransport`를 사용하고, `httpx.AsyncClient`는 `async with` 또는 fixture finalizer로 닫는다. |
| JSON 검증 | byte 문자열 포함 여부보다 `json.loads()` 또는 response `.json()`으로 구조를 검증한다. |
| 비동기 병렬성 검증 | wall-clock 시간 임계값에 의존하지 않는다. fake 객체의 동시 실행 카운터 등 계측값으로 검증한다. |
| FastAPI endpoint 의존성 교체 | 구현 클래스 monkeypatch보다 `app.dependency_overrides`를 우선 사용한다. |
| App-scoped 리소스 | endpoint 테스트에서 직접 만들지 않고 lifespan 또는 dependency override로 제공한다. |
| 필수 의존성 누락 | `NoneType` AttributeError가 아니라 설정 누락 예외를 검증한다. |

### Rationale

`conftest.py`는 pytest의 fixture discovery 메커니즘이다.
일반 상수/헬퍼까지 이 파일에 넣고 직접 import하면 테스트 의존성이 암묵적이 되고, fixture와 단순 데이터의 경계가 흐려진다.

HTTP payload를 byte substring으로 검사하면 공백, 직렬화 순서, 숫자 표현 방식에 흔들릴 수 있다.
콜백 JSON은 Spring DTO 계약이므로 필드 구조를 dict로 파싱해 검증한다.

비동기 병렬성 테스트에서 `elapsed < 0.09` 같은 시간 기준을 쓰면 CI 부하에 따라 flaky해질 수 있다.
병렬 실행 여부는 fake client 내부의 `max_active_count`처럼 테스트가 통제하는 계측값으로 확인한다.

FastAPI endpoint 테스트는 실제 앱의 dependency graph를 검증하는 성격이 강하다.
endpoint가 `Depends()`로 받는 협력 객체는 `app.dependency_overrides`로 교체하고, 테스트 종료 후 override를 정리한다.
HTTP client, DB client 같은 app-scoped 리소스가 필요한 endpoint는 lifespan-aware `TestClient` 또는 dependency override를 사용한다.
Service 내부 순수 로직 테스트는 생성자에 fake를 직접 주입해도 된다.
`monkeypatch`는 환경변수, 시간, 랜덤값처럼 dependency provider로 표현하기 어려운 경계에 제한적으로 사용한다.

필수 의존성 누락 테스트는 나중에 우연히 발생하는 `AttributeError`를 기대하지 않는다.
예를 들어 DB client가 없으면 Repository 조회 메서드 내부의 `database.from_()`까지 진행되기 전에, 생성자나 dependency provider에서 설정 누락 예외가 발생해야 한다.

### Examples

```python
# conftest.py
@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

```python
# tests/fixtures.py
REVIEW_ID = 7
REVIEW_CONTENT = "차분하고 공간감 있는 모달 재즈가 인상적입니다."
```

---

## Consequences

- 비용과 네트워크 상태에 의존하지 않는 빠른 테스트를 유지한다.
- 실패 시 Router, Service, Client/Repository 중 어느 레이어 문제인지 추적하기 쉽다.
- 비동기 API 응답 계약과 백그라운드 추천 처리 계약을 혼동하지 않는다.
- 테스트 함수명은 영문으로 유지하되, 문서와 docstring은 한글 설명을 허용한다.
- `conftest.py`, fixture 모듈, fake 객체의 책임이 분리되어 테스트 유지보수가 쉬워진다.
- HTTP/비동기 테스트가 직렬화 공백이나 CI timing에 덜 흔들린다.
- 테스트 fake는 외부 네트워크를 대체하되, 운영 dependency graph의 필수 주입 누락을 숨기지 않는다.
- 상세 테스트 케이스는 [flows/](../flows/)의 각 플로우 문서에 둔다.
