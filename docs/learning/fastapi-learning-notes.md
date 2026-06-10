# FastAPI 학습 노트

> pytest 학습 노트(`learning-notes.md`)와 별도로, FastAPI 프레임워크 개념을 정리한 문서입니다.
> `/explain-python` 커맨드가 자동으로 읽고 업데이트합니다.

최종 업데이트: 2026-06-10 (SimpleNamespace, ConfigurationError, getattr 안전 접근 추가)

---

## 배운 개념 목록

---

### Router — HTTP 진입점의 단일 책임

Router는 HTTP 요청/응답 경계만 담당한다.

```python
# recommend_router.py
@router.post("/review", status_code=status.HTTP_202_ACCEPTED)
async def recommend_by_review(
    request: RecommendByReviewRequest,
    background_tasks: BackgroundTasks,
    service: RecommendationService = Depends(get_recommendation_service),
) -> Response:
    background_tasks.add_task(service.recommend_by_review, ...)
    return Response(status_code=status.HTTP_202_ACCEPTED)
```

Router가 직접 하지 않는 것: OpenAI 호출, DB 조회, 추천 사유 생성, Spring 콜백 전송.
이 모든 건 Service가 담당하고, Router는 "요청을 받아서 Service에 넘기고 202를 반환"하는 것만 한다.

**왜 이렇게 하나?**
Router가 비즈니스 로직을 담으면 "HTTP 계층 테스트"와 "추천 처리 테스트"가 섞인다.
Router는 얇게 유지해야 "이 엔드포인트가 202를 반환하는가"만 테스트할 수 있다.

- ADR-BP001 Decision 1 참고

---

### `Depends()` — FastAPI 의존성 주입

FastAPI가 제공하는 의존성 주입 메커니즘.
함수 파라미터에 `Depends(provider_함수)`를 붙이면, FastAPI가 요청마다 provider 함수를 호출해서 반환값을 자동으로 주입한다.

```python
# 사용
service: RecommendationService = Depends(get_recommendation_service)

# provider
def get_recommendation_service() -> RecommendationService:
    return RecommendationService()
```

**반대 예시 — 직접 생성하면 어떤 문제가 생기나?**

```python
# 이전 코드 (문제 있음)
async def recommend_by_review(request, background_tasks):
    service = RecommendationService()  # Router가 조립 방식을 직접 앎
```

이렇게 하면 테스트에서 `RecommendationService`를 다른 객체로 교체할 방법이 없다.
`Depends()`를 쓰면 테스트에서 `app.dependency_overrides`로 교체할 수 있다 (아래 참고).

---

### `dependency_overrides` — 테스트에서 의존성 교체

`Depends()`를 쓴 코드를 테스트할 때, 실제 서비스 대신 fake로 교체하는 방법.

```python
# 테스트에서
def fake_service():
    return FakeRecommendationService()

app.dependency_overrides[get_recommendation_service] = fake_service

# 테스트 후 정리
app.dependency_overrides.clear()
```

Router 코드를 전혀 건드리지 않고도 의존성을 교체할 수 있다는 게 핵심.
`monkeypatch`로 클래스 자체를 패치하는 방식보다 FastAPI의 공식 교체 경로를 쓰는 것이 더 안전하다.

**`monkeypatch` vs `dependency_overrides` 선택 기준**
| 상황 | 방법 |
|---|---|
| FastAPI `Depends()`로 주입된 의존성 교체 | `dependency_overrides` |
| 모듈 수준 객체, 설정값, 외부 함수 임시 교체 | `monkeypatch` |

---

### `dependencies.py` — 의존성 조립 분리

Router가 어떤 클래스를 어떻게 조립하는지 알지 않도록, 조립 책임을 별도 파일로 분리한다.

```
app/
  api/
    recommend_router.py    ← HTTP 계층만
    dependencies.py        ← 조립 방식만
```

```python
# dependencies.py
def get_recommendation_service() -> RecommendationService:
    return RecommendationService()
```

지금은 단순해 보이지만, 나중에 DB 연결(Supabase client)이 필요해지면 이 파일만 수정한다:

```python
# 나중에 DB 연결이 추가되면
def get_recommendation_service(
    request: Request,
) -> RecommendationService:
    db = request.app.state.db  # lifespan에서 관리되는 DB client
    return RecommendationService(
        album_embedding_repository=AlbumEmbeddingRepository(database=db)
    )
```

Router 코드는 건드리지 않아도 된다.

- ADR-BP001 Decision 5 참고

---

### 객체 3종류 분류 — 생성 위치와 종료 책임

FastAPI 앱에서 모든 객체는 세 종류 중 하나다. 종류에 따라 **어디서 만들고, 어디서 닫는지**가 달라진다.

| 종류 | 예시 | 생성 위치 | 종료 위치 | 주입 방식 |
|---|---|---|---|---|
| Request-scoped 협력 객체 | Service, Repository wrapper, Client wrapper | Dependency provider | 종료 책임 없음 | `Depends()` |
| App-scoped 외부 리소스 | `httpx.AsyncClient`, DB client, OpenAI client | Lifespan startup | Lifespan shutdown | `request.app.state`를 통해 provider가 주입 |
| 순수 값/설정 | settings, TOP_K, model name | Config module | 종료 없음 | provider 또는 생성자 인자 |

**왜 구분이 중요한가?**

App-scoped 리소스(`httpx.AsyncClient` 등)를 Request-scoped처럼 매 요청마다 만들면:
- 연결 풀을 재사용하지 못해 성능이 떨어진다.
- `aclose()`를 호출하지 않으면 connection leak이 생긴다.

반대로 Request-scoped 객체(Service 등)를 App-scoped처럼 앱 시작 시 한 번만 만들면:
- 요청 간 상태가 공유되어 버그가 생길 수 있다.
- 테스트에서 `dependency_overrides`로 교체할 수 없게 된다.

**이 프로젝트 적용 예시:**

```
Request-scoped: RecommendationService, AlbumEmbeddingRepository, SpringCallbackClient
App-scoped:     httpx.AsyncClient, OpenAI async client, DB client
순수 값:        settings.RECOMMENDATION_TOP_K, settings.OPENAI_EMBEDDING_MODEL
```

- ADR-BP001 Decision 5 참고

---

### Decision 5 Rules — 6가지 생성 규칙

ADR이 명시한 규칙. 어디서 무엇을 만들면 안 되는지를 명확히 금지한다.

```
1. Router는 협력 객체를 직접 생성하지 않는다.
2. Service는 닫아야 하는 외부 리소스를 직접 생성하지 않는다.
3. Client wrapper는 닫아야 하는 리소스를 직접 만들지 않고 주입받는다.
4. 닫아야 하는 리소스는 lifespan에서 만들고 lifespan에서 닫는다.
5. Dependency provider는 app-scoped 리소스를 꺼내 request-scoped 객체를 조립한다.
6. 테스트는 dependency_overrides로 provider를 교체하거나,
   service 단위 테스트에서는 생성자에 fake를 직접 주입한다.
```

규칙 2가 이번에 추가된 핵심 포인트다. 이전엔 "Router가 생성하지 않는다"만 있었다면,
지금은 **Service도 `httpx.AsyncClient` 같은 리소스를 직접 만들면 안 된다**는 규칙이 명시됐다.

**반대 예시 — Service가 직접 만들면:**

```python
class SpringCallbackClient:
    def __init__(self):
        self.http_client = httpx.AsyncClient()  # Service가 직접 생성 → 규칙 3 위반
```

이 경우 `aclose()`를 호출할 타이밍이 없어서 connection leak이 발생할 수 있다.
올바른 방식은 lifespan에서 만든 client를 생성자로 주입받는 것이다.

---

### `BackgroundTasks` — 응답 후 비동기 처리

FastAPI 내장 기능. 응답을 먼저 반환하고, 그 이후에 태스크를 실행한다.

```python
background_tasks.add_task(
    service.recommend_by_review,
    request.review_id,
    request.review_content,
)
return Response(status_code=status.HTTP_202_ACCEPTED)
```

흐름:
```
클라이언트 요청
  → FastAPI: 202 즉시 반환
  → (응답 후) service.recommend_by_review() 실행
      → OpenAI 호출
      → pgvector 검색
      → Spring 콜백
```

**왜 필요한가?**
Spring Boot는 감상문 저장 트랜잭션 커밋 후 이 API를 호출한다.
Spring은 응답 body를 비즈니스 데이터로 쓰지 않으므로, FastAPI가 추천 처리가 끝날 때까지 기다리게 하면 Spring의 HTTP 타임아웃이 OpenAI/DB 지연에 묶인다.
`BackgroundTasks`로 분리하면 Spring은 202를 받고 즉시 연결을 끊고, FastAPI는 별도로 처리한다.

**한계**
`BackgroundTasks`는 프로세스 내에서 실행된다. FastAPI 프로세스가 죽으면 실행 중인 태스크도 유실된다.
유실이 허용되지 않는 운영 환경에서는 Celery/Redis 같은 별도 큐로 전환이 필요하다.

- ADR-BP001 Decision 1 Alternatives 참고

---

### `lifespan` — 앱 시작/종료 리소스 관리

HTTP client, DB connection처럼 앱 시작 시 생성하고 종료 시 닫아야 하는 리소스를 관리하는 FastAPI 패턴.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 실행
    app.state.http_client = httpx.AsyncClient()
    yield
    # 앱 종료 시 실행 (yield 이후)
    await app.state.http_client.aclose()

app = FastAPI(lifespan=lifespan)
```

**왜 필요한가?**
`httpx.AsyncClient()`를 매 요청마다 생성하면 연결 풀을 재사용하지 못해 성능이 떨어진다.
`lifespan`에서 한 번 생성하고 `app.state`에 저장해두면 모든 요청에서 같은 클라이언트를 재사용한다.

이 프로젝트의 운영 경로에서는 `SpringCallbackClient`가 내부에서 `httpx.AsyncClient()`를 직접 생성하지 않는다.
lifespan에서 만든 HTTP client를 dependency provider가 `SpringCallbackClient(http_client=...)`로 주입한다.

- ADR-BP001 Decision 5 참고

---

### `app.state` — 앱 수준 공유 상태

`lifespan`에서 생성한 리소스를 라우터/의존성에서 접근하는 방법.

```python
# lifespan에서 저장
app.state.db = create_db_client()

# dependency에서 접근
def get_repo(request: Request) -> AlbumEmbeddingRepository:
    return AlbumEmbeddingRepository(database=request.app.state.db)
```

`app.state`는 FastAPI 앱 인스턴스에 붙은 딕셔너리처럼 동작한다.
전역 변수로 DB client를 두는 것과 비슷하지만, 앱 인스턴스에 묶여 있어 테스트에서 앱을 새로 만들면 state도 초기화된다.

---

### `TestClient` with 블록 — lifespan 실행 보장

`conftest.py`의 `client` fixture가 `with TestClient(app) as test_client:` 형태를 쓰는 이유.

```python
@pytest.fixture
def client():
    app.dependency_overrides.clear()      # 이전 테스트 잔여 override 정리
    with TestClient(app) as test_client:  # lifespan startup 실행
        yield test_client
    app.dependency_overrides.clear()      # 이 테스트 override 정리
```

**`with` 없이 생성하면 어떤 문제가 생기나?**

```python
client = TestClient(app)   # lifespan 실행 안 됨 — app.state.db 등 미초기화
```

lifespan에서 DB/OpenAI/HTTP client를 `app.state`에 등록하므로, `with` 없이 만든 TestClient는 필요한 app state가 없어서 테스트가 깨진다.
따라서 endpoint 테스트는 `with TestClient(app) as test_client:` 또는 이를 감싼 fixture를 사용한다.

---

### `dependency_overrides` 앞뒤 clear — 테스트 오염 방지

`app.dependency_overrides`는 앱 인스턴스에 붙어 있어서 테스트 간에 공유된다.

```python
# 테스트 A — override 설정 후 안 지우면
app.dependency_overrides[get_recommendation_service] = lambda: FakeService()

# 테스트 B — 아무것도 안 했는데 Fake가 주입됨 → 테스트 결과가 실행 순서에 의존
```

fixture에서 앞뒤로 `.clear()`를 호출하는 이유:
- **앞**: 이전 테스트가 남긴 잔여 override 제거
- **뒤**: 이 테스트가 설정한 override 제거

테스트가 독립적으로 실행되려면 각 테스트가 상태를 깨끗하게 시작하고 끝내야 한다.
이걸 "테스트 격리(test isolation)"라고 한다.

- ADR-BP003 Decision 5 참고

---

### Dependency Wiring 테스트 — 운영 조립 경로 검증

외부 네트워크는 fake로 대체하지만, **"올바른 객체가 올바른 위치에 주입되는가"** 는 별도로 검증해야 한다.

**왜 필요한가?**

fake 테스트만 있으면 이런 함정이 생긴다:

```python
# 테스트 — fake 주입이라 항상 통과
service = RecommendationService(album_embedding_repository=FakeRepo())

# 운영 — provider가 database=None으로 Repository를 조립
# → Repository.find_similar_albums() 호출 시점에 AttributeError: 'NoneType' has no attribute 'from_'
```

ADR이 말하는 원칙: "나중에 우연히 발생하는 `AttributeError`를 기대하지 않는다."
에러가 쿼리 실행 시점이 아니라 **생성자나 provider에서 먼저 터져야** 한다.

**검증 시나리오 (ADR Decision 2-1)**

| 시나리오 | 기댓값 |
|---|---|
| `AlbumEmbeddingRepository(database=None)` 직접 생성 | 설정 누락 예외 발생 (AttributeError 아님) |
| OpenAI/HTTP client wrapper에 필수 client 없음 | 설정 누락 예외 발생 |
| `app.state`에 필수 리소스 있음 | provider가 해당 client로 Repository/Service/Client wrapper 조립 |
| `app.state`에 필수 리소스 없음 | provider가 설정 누락 예외 발생 |
| lifespan shutdown 실행 | 닫아야 하는 client의 close hook 호출 |
| Service 테스트에서 fake repository 주입 | 실제 DB client 없이 유스케이스 분기 검증 가능 |

이 테스트는 실제 Supabase에 연결하지 않는다.
**fake DB/OpenAI/HTTP client를 사용하되, fake가 운영 wiring 경로에 주입되고 종료 hook이 호출되는지 검증**한다.

- ADR-BP003 Decision 2-1 참고

---

### `ConfigurationError` — 설정 누락을 명확한 예외로 표현

`exceptions.py`에 새로 추가된 예외 클래스.

```python
class ConfigurationError(RecommendationError):
    pass
```

**왜 `AttributeError`나 `NoneType` 오류 대신 쓰나?**

```python
# 나쁜 예 — database가 None이면 나중에 AttributeError 발생
class AlbumEmbeddingRepository:
    def __init__(self, database):
        self.database = database  # None이어도 그냥 저장

    async def find_similar_albums(self, ...):
        self.database.from_(...)  # ← 여기서 AttributeError: 'NoneType' has no attribute 'from_'
```

```python
# 좋은 예 — 생성자에서 즉시 ConfigurationError 발생
class AlbumEmbeddingRepository:
    def __init__(self, database):
        if database is None:
            raise ConfigurationError("database client is required")
        self.database = database
```

나쁜 예는 에러가 **조회 메서드 실행 시점**에 터진다. 어디서 `None`이 들어왔는지 역추적해야 한다.
좋은 예는 에러가 **생성 시점**에 터진다. "설정이 잘못됐다"는 의도가 명확하고, 어느 줄에서 문제인지 즉시 알 수 있다.

ADR-BP003 Decision 5: "필수 의존성 누락은 `NoneType` AttributeError가 아니라 설정 누락 예외를 검증한다."

---

### `getattr(obj, name, default)` — 속성 안전 접근

`dependencies.py`에서 `app.state.database`에 접근할 때 사용하는 패턴.

```python
database = getattr(request.app.state, "database", None)
```

**왜 `request.app.state.database`로 직접 접근하지 않나?**

```python
# 직접 접근 — database가 없으면 AttributeError 발생
database = request.app.state.database  # AttributeError: 'State' has no attribute 'database'

# getattr 안전 접근 — 없으면 None 반환
database = getattr(request.app.state, "database", None)  # None 반환
if database is None:
    raise ConfigurationError("app.state.database is not configured.")
```

`getattr(객체, "속성명", 기본값)` — 3개 인자 형태가 핵심이다. 속성이 없으면 `AttributeError` 대신 기본값을 반환한다.

이렇게 하면 에러 메시지를 직접 제어할 수 있다:
- `AttributeError: 'State' has no attribute 'database'` (의미 불명확)
- `ConfigurationError: app.state.database is not configured.` (설정 누락임이 명확)

---

### `SimpleNamespace` — 테스트용 가짜 객체 즉석 생성

`test_dependencies.py`에서 `request` 객체를 흉내 낼 때 사용.

```python
from types import SimpleNamespace

def make_request(database=None, has_database=True):
    state = SimpleNamespace()
    if has_database:
        state.database = database
    app = SimpleNamespace(state=state)
    return SimpleNamespace(app=app)
```

`SimpleNamespace`는 점(`.`) 접근이 가능한 빈 객체를 만든다. 이렇게 만든 객체는 실제 FastAPI `Request`처럼 `request.app.state.database` 접근이 가능하다.

**`type()` 동적 생성(저번에 배운 개념)과 비교**

| | `SimpleNamespace` | `type()` |
|---|---|---|
| 용도 | 속성 접근이 필요한 가짜 객체 | 메서드가 있는 1회성 클래스 |
| 문법 | `ns = SimpleNamespace(); ns.x = 1` | `type("Cls", (), {"x": 1})` |
| 적합한 경우 | DTO, state, request처럼 데이터만 담는 객체 | 메서드가 있는 응답 객체 |

`request.app.state`처럼 데이터 담는 구조체를 흉내 낼 때는 `SimpleNamespace`가 더 읽기 쉽다.

---

### `pytest.raises(match=...)` — 예외 메시지까지 검증

저번에 배운 `pytest.raises()`에 `match` 인자를 추가한 패턴.

```python
with pytest.raises(ConfigurationError, match="app.state.database"):
    get_recommendation_service(request)
```

`match`는 예외 메시지에 해당 문자열이 포함되는지 검증한다 (정규식도 가능).

**왜 `match`까지 쓰나?**

```python
# match 없이 — 예외 타입만 검증
with pytest.raises(ConfigurationError):
    ...
# "어떤 이유로 ConfigurationError가 났는가"는 모름

# match 있음 — 예외 메시지까지 검증
with pytest.raises(ConfigurationError, match="app.state.database"):
    ...
# "app.state.database 누락 때문에 난 ConfigurationError"임을 검증
```

`ConfigurationError`가 여러 곳에서 발생할 수 있을 때, `match`로 **어떤 설정이 누락됐는지**까지 고정할 수 있다.

---

### 저번에 배운 개념과의 연결

**의존성 주입 (pytest 버전 → FastAPI 버전)**
`learning-notes.md`에서 배운 의존성 주입은 `__init__`으로 외부에서 받는 패턴이었다.
FastAPI의 `Depends()`는 같은 원리를 HTTP 요청 수준으로 확장한 것이다.

```
pytest 버전:  EmbeddingService(openai_client=fake_client)  → 생성자 주입
FastAPI 버전: Depends(get_recommendation_service)          → 요청 단위 주입
```

둘 다 "호출자가 구현체를 결정한다"는 원칙은 동일하다.

**Fake 객체 패턴 → `dependency_overrides`**
`learning-notes.md`의 Fake 객체 패턴은 생성자에 직접 fake를 넘겼다.
FastAPI에서는 `dependency_overrides`가 그 역할을 한다 — Router를 수정하지 않고 의존성을 교체하는 공식 경로.
