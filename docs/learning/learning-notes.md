# Python 학습 노트

> 이 파일은 `/explain-python` 커맨드가 자동으로 읽고 업데이트합니다.
> 새로 배운 개념은 아래에 추가됩니다.

최종 업데이트: 2026-06-11 (recommendation_service.py)

---

## 배운 개념 목록

<!-- 개념이 추가될 위치 -->

### pytest fixture
- 테스트 함수의 매개변수 이름과 같은 이름의 `@pytest.fixture` 함수를 pytest가 자동으로 찾아 주입한다.
- `conftest.py`에 선언한 fixture는 같은 디렉터리 및 하위 디렉터리의 모든 테스트에서 자동으로 사용 가능하다.
- `yield`를 사용하면 테스트 종료 후 정리 코드(teardown)를 실행할 수 있다.
- 파일: `backendPython/tests/conftest.py`, `backendPython/tests/integration/test_recommendation_flow.py`

### monkeypatch - 임시 교체
- pytest 내장 fixture. `monkeypatch.setattr(대상객체, "속성명", 새값)`으로 테스트 중 코드를 임시 교체한다.
- 테스트가 끝나면 자동으로 원래 값으로 복구된다.
- 외부 의존성(OpenAI, DB 등)을 실제로 호출하지 않고 가짜 함수로 대체할 때 사용한다.
- 파일: `backendPython/tests/integration/test_recommendation_flow.py`
- **써야 할 때**: 테스트가 값을 직접 심고, 그 값이 전달되는지 확인할 때
  - 예: `monkeypatch.setattr(settings, "MODEL", "gpt-4")` → `assert calls[0]["model"] == "gpt-4"`
- **쓰지 말아야 할 때**: 설정 파일이 관리하는 값을 그대로 검증할 때
  - 예: `assert calls[0]["model"] == settings.OPENAI_CHAT_MODEL` → monkeypatch 불필요, settings 상수로 직접 검증
- monkeypatch로 심은 값을 기대값에서 `settings`로 읽으면 "settings == settings"가 되어 의미 없는 테스트가 됨

### spy 패턴
- 실제 로직을 실행하지 않고 "어떤 인자로 호출됐는가"만 기록하는 가짜 함수.
- `calls = []` 리스트를 클로저로 캡처해, spy 함수가 호출될 때마다 인자를 append한다.
- 테스트 마지막에 `assert calls == [...]`로 호출 여부와 인자를 검증한다.
- 교체할 원본이 `async def`면 spy도 반드시 `async def`로 작성해야 한다.
- ADR-BP003 Decision 5: 외부 의존성 fake는 테스트 파일 안에 작게 둔다.
- 파일: `backendPython/tests/integration/test_recommendation_flow.py`

### TestClient (FastAPI)
- 실제 서버 포트를 열지 않고 FastAPI 앱에 HTTP 요청을 보낼 수 있는 테스트 도구.
- 내부적으로 `httpx`를 사용해 ASGI 앱에 직접 요청을 전달한다.
- ADR-BP003: 외부 네트워크 없이 HTTP 상태코드·응답 본문을 검증하는 원칙에 부합한다.
- 파일: `backendPython/tests/conftest.py`

### ASGI (Asynchronous Server Gateway Interface)
- Python 웹 앱과 웹 서버 사이의 통신 규약(인터페이스).
- WSGI(동기, Flask/Django)의 후속. 비동기를 지원해 여러 요청을 동시에 처리할 수 있다.
- FastAPI가 `async def`로 동시 처리가 가능한 이유가 ASGI 기반이기 때문.
- 운영: `브라우저 → uvicorn(웹 서버) → [ASGI] → FastAPI 앱`
- TestClient: `테스트 코드 → httpx → [ASGI 직접 구현] → FastAPI 앱` — uvicorn 없이도 동작하는 이유.
- 파일: `backendPython/tests/conftest.py`

### Fake 객체
- 실제 외부 의존성(DB, API)을 흉내 내는 가짜 클래스. spy와 달리 실제처럼 동작한다.
- spy: 호출 여부·인자만 기록 / fake: 실제 동작을 흉내 냄
- ADR-BP003 Decision 5: 외부 의존성 fake는 테스트 파일 안에 작게 둔다.
- 파일: `backendPython/tests/unit/test_album_embedding_repository.py`

> 참고: 
> - 인자: 함수 호출에 넘기는 값
> - 파라미터(매개변수) : 함수 정의에 설정된 변수명

### 메서드 체이닝과 `return self`
- 메서드가 `return self`를 반환하면 `.method1().method2().method3()` 처럼 연속 호출이 가능하다.
- Fake 객체에서 체이닝을 구현할 때 각 메서드에 `return self`를 붙인다.
- `return self` 없이 체이닝하면 `AttributeError: 'NoneType' has no attribute ...` 발생.
- 파일: `backendPython/tests/unit/test_album_embedding_repository.py`

### `type()` 동적 클래스 생성
- `type("클래스명", (부모,), {"속성": 값})`으로 클래스를 즉석에서 생성한다.
- 1회성 단순 응답 객체처럼 정식 클래스 선언이 과한 경우에만 사용. 남용 시 가독성·자동완성 손실.
- 파일: `backendPython/tests/unit/test_album_embedding_repository.py`

### `@pytest.mark.asyncio`
- `async def` 테스트 함수를 pytest가 실행할 수 있게 해주는 데코레이터.
- 마크 없이 `async def` 테스트를 작성하면 코루틴 객체만 반환되고 실제로 실행되지 않아 항상 통과해버린다.
- 파일: `backendPython/tests/unit/test_album_embedding_repository.py`

### `pytest.raises()` — 예외 검증
- `with pytest.raises(예외타입):` 블록 안에서 해당 예외가 발생하지 않으면 테스트 실패.
- 외부 오류(RuntimeError 등)를 내부 예외(RepositoryError)로 감싸는 계약을 검증할 때 사용.
- 예외 감싸기(Exception Wrapping): 레이어 간 결합도를 낮추는 패턴. 상위 레이어는 외부 기술(Supabase 등)을 몰라도 됨.
- 파일: `backendPython/tests/unit/test_album_embedding_repository.py`

### 의존성 주입 (Dependency Injection)
- 클래스가 필요한 객체를 직접 생성하지 않고, 외부에서 받는 패턴.
- `__init__(self, openai_client)`처럼 받으면 테스트에서 fake로 교체할 수 있는 자리가 생긴다.
- 의존성 주입 없이는 fake를 끼워넣을 자리 자체가 없어서 격리 테스트가 불가능하다.
- 테스트만을 위한 패턴이 아님 — 운영 환경에서도 구현체를 교체할 수 있게 해줌.
- 파일: `backendPython/tests/unit/test_recommendation_reason_service.py`

### 덕 타이핑 (Duck Typing)
- "오리처럼 걷고 오리처럼 울면 오리다" — 타입이 아니라 메서드/속성이 있는지로 판단.
- Python은 타입을 강제하지 않아서 `.chat.completions.create()`만 있으면 진짜 OpenAI 클라이언트든 fake든 동일하게 동작한다.
- 의존성 주입 + 덕 타이핑 조합이 fake 객체 패턴의 핵심 원리.
- 파일: `backendPython/tests/unit/test_recommendation_reason_service.py`

### 리스트 컴프리헨션 (List Comprehension)
- `[표현식 for 변수 in 반복가능객체]` 형태로 리스트를 한 줄로 만드는 Python 문법.
- `for` 반복문 + `append`를 한 줄로 압축한 것과 동일하다.
- 테스트에서 객체 리스트에서 특정 필드만 뽑아 순서를 검증할 때 자주 쓰인다.
- 예: `[candidate.album_id for candidate in result] == ["1", "2"]`
- 파일: `backendPython/tests/unit/test_album_embedding_repository.py`

### `Decimal` — 정확한 소수점 타입
- Python `float`은 이진수 표현으로 오차가 생김 (`0.1 + 0.2 != 0.3`).
- 추천 점수처럼 정확한 소수점이 필요한 필드에 `Decimal`을 사용한다.
- 반드시 문자열로 초기화해야 정확함: `Decimal("0.9423")` (O) / `Decimal(0.9423)` (X — float을 거쳐 오차 발생)
- 파일: `backendPython/tests/unit/test_recommendation_schema.py`

### `dump_alias` — by_alias 직렬화
- Pydantic 모델을 `by_alias=True`로 직렬화하면 내부 snake_case 필드명 대신 설정된 alias(camelCase)로 출력된다.
- `fixtures.py`에 헬퍼로 두는 이유: 여러 테스트 파일에서 공유하기 때문 (ADR-BP003 Decision 5).
- ADR-BP003 Decision 3: Spring 콜백은 camelCase 계약이므로 실제로 camelCase로 직렬화되는지 검증할 때 사용.
- Pydantic은 기본적으로 필드를 Python 변수명(snake_case)으로 저장하므로 alias를 설정하지 않으면 `model_dump()`는 항상 snake_case를 반환한다.
- FastAPI가 JSON 응답을 보낼 때 내부적으로 `by_alias=True`로 직렬화하므로, alias 설정이 곧 실제 네트워크 페이로드가 된다.
- `dump_alias`를 테스트에 쓰는 이유:
  - `RecommendationCallbackItem`: alias(`albumId` 등 camelCase)가 올바르게 설정됐는지 검증
  - `RecommendByReviewRequest`: alias가 실수로 추가되지 않았는지(snake_case 유지) 검증
- 파일: `backendPython/tests/fixtures.py`, `backendPython/tests/unit/test_recommendation_schema.py`

### 팩토리 메서드 패턴 (`completed`, `failed`)
- 인스턴스를 직접 생성하지 않고, 클래스 메서드로 올바른 필드 조합을 강제하는 패턴.
- 성공/실패처럼 상태에 따라 필드 조합이 달라질 때 실수를 방지한다.
- 예: `RecommendationCallbackRequest.completed([item])` / `.failed(error_code=..., message=...)`
- 파일: `backendPython/tests/unit/test_recommendation_schema.py`

### fixture vs 일반 import 선택 기준
- **생성/정리가 필요한 자원** (DB 연결, HTTP 클라이언트, 임시 파일) → `conftest.py` fixture
- **단순 상수·데이터** → `fixtures.py` 일반 import (`from tests.fixtures import ...`)
- **특정 파일에서만 쓰는 가짜 객체** → 테스트 파일 안에 직접
- 핵심: fixture의 본질은 "생명주기 관리(setup/teardown)"이지, 단순히 "값을 공유하는 수단"이 아니다.
- `yield`가 없는 fixture는 teardown이 없다는 뜻 — 이 경우 일반 import가 더 적합할 수 있다.
- ADR-BP003 Decision 5: `conftest.py`는 pytest fixture만 두는 것이 원칙.
- 파일: `backendPython/tests/conftest.py`, `backendPython/tests/fixtures.py`

### `dependency_overrides` — FastAPI 의존성 교체
- `app.dependency_overrides[원본함수] = lambda: 가짜객체` 로 테스트 중 의존성을 교체한다.
- monkeypatch가 클래스 메서드를 직접 덮어쓰는 것과 달리, `dependency_overrides`는 FastAPI의 DI 컨테이너를 통해 교체하므로 실제 요청 흐름(`Depends()` → 엔드포인트)을 그대로 테스트한다.
- **monkeypatch와의 차이**:
  - `monkeypatch.setattr(RecommendationService, "recommend_by_review", spy)` → 클래스 자체를 패치 (FastAPI DI 우회)
  - `app.dependency_overrides[get_recommendation_service] = lambda: Fake()` → DI 경로를 유지하면서 구현체만 교체
- `Depends()`로 주입된 의존성을 교체할 때는 반드시 `dependency_overrides`를 사용해야 한다.
- 파일: `backendPython/tests/integration/test_recommendation_flow.py`, `backendPython/app/api/dependencies.py`

### `dependency_overrides.clear()` — 테스트 격리
- `dependency_overrides`는 `app` 객체에 딕셔너리로 저장되므로, 테스트 간에 공유된다.
- 한 테스트에서 교체한 의존성이 다음 테스트에 영향을 주는 것을 "테스트 오염(test pollution)"이라 한다.
- `conftest.py`의 `client` fixture에서 테스트 시작 전·후에 각각 `.clear()`를 호출해 격리한다.
- 파일: `backendPython/tests/conftest.py`

### `ConfigurationError` — 명시적 설정 누락 예외
- `None` 체크 후 `raise ConfigurationError(메시지)`로 "왜 실패했는지"를 명확히 알린다.
- `NoneType has no attribute ...` 같은 암묵적 오류 대신 명시적 예외를 던지는 것이 디버깅에 유리하다.
- `pytest.raises(ConfigurationError, match="키워드")`로 예외 타입과 메시지를 함께 검증한다.
- 파일: `backendPython/app/core/exceptions.py`, `backendPython/tests/unit/test_dependencies.py`

### 센티널 패턴 — `object()`로 고유한 "없음" 신호 만들기
- `DEFAULT = object()` / `MISSING = object()` — 세상에 딱 하나뿐인 객체를 만들어 고유한 신호로 사용.
- `None`은 "유효한 값"이 될 수 있어서 "값을 안 넘긴 것"과 "명시적으로 None을 넘긴 것"을 구분할 수 없을 때 씀.
- `is` 비교로만 구분: `if x is DEFAULT:` → 인자를 안 넘긴 상태 / `if x is MISSING:` → 해당 속성을 아예 만들지 말 것.
- Python 표준 라이브러리(`functools`, `inspect`)도 같은 패턴 사용.
- 파일: `backendPython/tests/unit/test_dependencies.py`

### `setattr(obj, name, value)` — 동적 속성 설정
- `state.database = x`와 `setattr(state, "database", x)`는 동일.
- 속성 이름이 문자열 변수일 때(반복문, parametrize 등) 직접 `.`으로 쓸 수 없으므로 `setattr` 사용.
- `for name, value in items(): setattr(state, name, value)` — 반복문으로 여러 속성을 한 번에 설정.
- 파일: `backendPython/tests/unit/test_dependencies.py`

### `**{key: value}` 언패킹 — 동적 키워드 인자 전달
- `make_request(**{"database": MISSING})` == `make_request(database=MISSING)`.
- 인자 이름이 문자열 변수일 때 딕셔너리로 만들어 언패킹하면 동적으로 인자 이름을 지정할 수 있다.
- `parametrize`에서 넘어온 문자열을 인자 이름으로 쓸 때 자주 등장하는 패턴.
- 파일: `backendPython/tests/unit/test_dependencies.py`

### `@pytest.mark.parametrize` — 같은 테스트를 여러 입력으로 반복
- `@pytest.mark.parametrize("변수명", [값1, 값2, ...])` — pytest가 자동으로 각 값으로 테스트를 반복 실행.
- 복붙 없이 같은 검증 로직을 여러 입력에 적용. 나중에 케이스 추가 시 리스트에 한 줄만 추가.
- 테스트 ID가 `test_이름[값]` 형태로 자동 생성되어 어느 케이스가 실패했는지 명확히 보임.
- 파일: `backendPython/tests/unit/test_dependencies.py`

### `SimpleNamespace` — 경량 가짜 객체
- `from types import SimpleNamespace`로 임포트. 동적으로 속성을 붙일 수 있는 빈 객체.
- `obj = SimpleNamespace(a=1, b=2)` → `obj.a == 1` (키워드 인자 이름이 그대로 속성 이름이 됨)
- Fake 클래스를 따로 선언하지 않고 단순한 구조체가 필요할 때 사용한다.
- FastAPI `request.app.state.database` 같은 중첩 구조를 흉내 낼 때 사용:
  - `state = SimpleNamespace(); setattr(state, "database", fake_db)`
  - `app = SimpleNamespace(state=state)`
  - `request = SimpleNamespace(app=app)` → `request.app.state.database == fake_db`
- 실제 FastAPI `Request` 객체는 ASGI scope 딕셔너리 전체가 필요해 직접 생성이 오히려 복잡하다.
- `type()` 동적 클래스 생성과 비슷하지만, 중첩 구조를 표현하기 더 자연스럽다.
- 파일: `backendPython/tests/unit/test_dependencies.py`

### `TestClient` vs `SimpleNamespace` — 테스트 방법 선택 기준
- 전 세계 기준으로 `TestClient` + `dependency_overrides`가 압도적으로 많이 쓰임. FastAPI 공식 권장.
- `SimpleNamespace`로 request를 흉내 내는 건 dependency provider 함수 자체를 단위 테스트할 때만 쓰는 패턴.

| 방법 | 목적 | 언제 |
|---|---|---|
| `TestClient` | HTTP 흐름 전체 검증 | "HTTP 202가 잘 오는가?" |
| `SimpleNamespace` | 특정 함수만 격리 검증 | "state에서 client를 잘 꺼내는가?" |

- 이 프로젝트가 둘 다 쓰는 이유: ADR-BP003 Decision 2-1 — "운영 dependency graph 자체를 별도 테스트로 고정". `TestClient`만으로는 `None` 전달 시 `ConfigurationError` 케이스를 깔끔하게 검증하기 어렵다.
- 파일: `backendPython/tests/unit/test_dependencies.py`, `backendPython/tests/integration/test_recommendation_flow.py`

### `getattr(obj, key, default)` — 안전한 속성 접근
- `obj.key`는 속성이 없으면 `AttributeError`를 발생시킨다.
- `getattr(obj, "key", None)`은 속성이 없으면 `None`을 반환한다.
- 런타임에 속성 존재 여부가 불확실한 경우(예: `app.state.database` 미설정)에 사용한다.
- 파일: `backendPython/app/api/dependencies.py`

### `Optional[타입]` — None 허용 타입 힌트
- `Optional[X]`는 "이 값은 `X`이거나 `None`이다"라는 선언. Python 3.10+에서는 `X | None`으로도 쓴다.
- Python은 타입을 강제하지 않지만, IDE와 사람이 "None을 넘겨도 된다"는 의도를 읽을 수 있다.
- 파일: `backendPython/app/services/recommendation_service.py`

### `A or B` 패턴 — None이면 기본값 사용
- `self.x = injected or Default()` — 주입된 값이 없으면(None) 기본 구현체를 만든다.
- Python `or`는 왼쪽이 falsy(None, 0, 빈 문자열 등)이면 오른쪽을 반환한다.
- **의존성 주입 + or 패턴**: 테스트에서는 fake를 주입하고, 운영에서는 None을 넘기면 기본값이 사용된다.
- `or` 패턴을 쓰지 않고 `ConfigurationError`를 던지는 경우: 기본 구현체를 만들 수 없을 때 (DB client 필요 등).
- 파일: `backendPython/app/services/recommendation_service.py`

### `async def` / `await` — 비동기 함수
- `async def`로 선언한 함수는 `await`해야 실제로 실행된다. 선언만으로는 아무것도 실행되지 않는다.
- `await` 지점에서 Python이 "나 지금 기다리는 중"이라고 양보해 다른 작업이 실행될 수 있다.
- 이전에 배운 `@pytest.mark.asyncio`가 필요한 이유: pytest가 `async def` 테스트를 대신 `await`해줘야 하기 때문.
- `asyncio.gather(a(), b())`로 여러 await를 동시에 실행할 수 있다 — ADR-BP002 Decision 4: 추천 사유 병렬 생성.
- 파일: `backendPython/app/services/recommendation_service.py`

### `try / except` — 예외 처리
- `try` 블록 안에서 예외 발생 시 `except`로 이동. 예외 없으면 `except` 건너뜀.
- `except SpecificError:` — 해당 타입의 예외만 잡는다. 다른 예외는 그대로 전파된다.
- `return`을 함께 쓰면 실패 처리 후 함수를 즉시 종료한다 (다음 단계 진행 방지).
- 저번에 배운 예외 감싸기와 연결: `EmbeddingError`가 OpenAI 내부 예외를 감싸므로 서비스는 OpenAI를 직접 몰라도 됨.
- 파일: `backendPython/app/services/recommendation_service.py`

### `if not collection` — 빈 컬렉션 체크
- Python에서 빈 리스트 `[]`, 빈 dict `{}`, `None`은 모두 **falsy**. `not []`는 `True`.
- `if not candidates:` — 후보가 없으면 이 블록 실행.
- 반대 예시: `if candidates is None:` — None만 체크하므로 빈 리스트 `[]`를 잡지 못한다.
- ADR-BP002 Decision 7: 추천 후보 0건은 실패로 간주.
- 파일: `backendPython/app/services/recommendation_service.py`

### 딕셔너리 컴프리헨션
- `{키: 값 for 변수 in 반복가능객체}` — 리스트 컴프리헨션의 딕셔너리 버전.
- 리스트 컴프리헨션: `[값 for ...]` / 딕셔너리 컴프리헨션: `{키: 값 for ...}`
- 용도: `album_id → 추천사유` 매핑을 만들어 O(1)로 빠르게 조회.
- `.get(key, default)`: 키가 없으면 default 반환 — 사유 생성이 누락된 앨범에 빈 문자열 사용.
- 파일: `backendPython/app/services/recommendation_service.py`

### `_` 접두사 — private 관례
- Python에는 진짜 private이 없다. `_`는 "클래스 내부에서만 쓰세요"라는 약속(관례).
- 외부에서 `obj._method()`로 호출은 가능하지만, 내부 구현이라는 신호이므로 테스트에서 직접 호출하지 않는다.
- public 메서드(`recommend_by_review`)의 결과만 검증하면 내부 구현이 바뀌어도 테스트가 깨지지 않는다.
- 파일: `backendPython/app/services/recommendation_service.py`

### `logging` — 운영 로그
- `logger = logging.getLogger(__name__)` — 현재 모듈명으로 logger 생성. 어느 파일 로그인지 자동 표시.
- `print()`와 달리 레벨(DEBUG/INFO/WARNING/ERROR), 시간, 모듈명과 함께 기록.
- `logger.exception(msg, exc)` — ERROR 레벨 + 스택 트레이스까지 함께 기록.
- ADR-BP002 Decision 7: Spring 콜백 전송 실패 시 로그만 기록, 자동 재시도 없음.
- 파일: `backendPython/app/services/recommendation_service.py`

### `monkeypatch.setattr` — 모듈 수준 함수 교체
- 저번엔 클래스 메서드를 교체했지만, `monkeypatch.setattr(모듈객체, "함수명", 가짜함수)`로 모듈 안의 함수도 교체할 수 있다.
- 용도: FastAPI lifespan에서 호출하는 팩토리 함수(`create_database_client` 등)를 가짜로 바꿔 실제 DB 연결을 막는다.
- **클래스 메서드 교체 vs 모듈 함수 교체**:
  - `monkeypatch.setattr(MyClass, "method", fake)` → 클래스 인스턴스 메서드 교체
  - `monkeypatch.setattr(module, "function", fake)` → 모듈 최상위 함수 교체
- 파일: `backendPython/tests/conftest.py`

### `raising=False` — 없는 속성도 허용
- `monkeypatch.setattr`의 기본값은 `raising=True`: 교체할 속성이 없으면 `AttributeError` 발생.
- `raising=False`: 속성이 없어도 에러 없이 새로 추가한다.
- 사용 시점: 모듈이 아직 해당 함수를 정의하지 않았거나, 이미 임포트된 모듈에서 이름이 없을 때.
- 파일: `backendPython/tests/conftest.py`

### `with TestClient(app)` — lifespan 실행
- `TestClient(app)`을 `with` 블록으로 쓰면 FastAPI **lifespan**이 실행된다.
- **lifespan**: 앱 시작(`startup`)과 종료(`shutdown`) 시 실행되는 코드 블록. DB 연결 생성/닫기가 여기 들어간다.
- `with` 없이 쓰면 lifespan이 실행되지 않아 `app.state`에 리소스가 없는 상태로 테스트된다.
- **순서가 중요**: monkeypatch로 팩토리 함수를 교체한 **뒤에** `with TestClient` 블록을 열어야 한다. 순서가 바뀌면 실제 DB 연결을 시도한다.
- ADR-BP003 Decision 2-1: lifespan 테스트는 startup에서 리소스가 `app.state`에 등록되고 shutdown에서 닫히는지 검증한다.
- 파일: `backendPython/tests/conftest.py`

### Fake 객체 — close 인터페이스 맞추기 (보충)
- `FakeDatabaseClient.close()` (동기) vs `FakeAsyncClient.aclose()` (비동기) — 실제 클라이언트와 메서드명을 맞춰야 한다.
- FastAPI lifespan shutdown이 각 client의 close 메서드를 호출하므로, fake도 동일한 인터페이스를 갖춰야 `AttributeError` 없이 종료된다.
- 파일: `backendPython/tests/conftest.py`, `backendPython/tests/unit/test_lifespan.py`

### `assert x is y` — 동일 객체 검사
- `==`는 값이 같은지, `is`는 메모리에서 완전히 같은 객체인지 검사한다.
- lifespan 테스트에서 `assert client.app.state.database is fake_db`로 "lifespan이 monkeypatch로 심은 팩토리 함수를 실제로 호출해 그 반환값을 저장했는가"를 검증한다.
- 만약 lifespan이 팩토리 함수를 무시하고 직접 객체를 생성하면 `is` 검증이 실패한다.
- 파일: `backendPython/tests/unit/test_lifespan.py`

### `@asynccontextmanager` — lifespan 작동 원리
- `@asynccontextmanager`는 `async def` 함수를 `with` 블록에 쓸 수 있게 만드는 데코레이터.
- `yield` 전 = startup, `yield` = 앱 실행 구간, `yield` 후 = shutdown.
- `try / finally` + `yield` 조합: 테스트에서 예외가 발생해도 `finally`가 반드시 실행 → shutdown(close) 보장.
- ADR-BP001 Decision 5: lifespan이 app-scoped 리소스 lifecycle을 담당한다.
- 파일: `backendPython/app/main.py`, `backendPython/tests/unit/test_lifespan.py`
