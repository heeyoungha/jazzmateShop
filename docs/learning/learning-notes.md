# Python 학습 노트

> 이 파일은 `/explain-python` 커맨드가 자동으로 읽고 업데이트합니다.
> 새로 배운 개념은 아래에 추가됩니다.

최종 업데이트: 2026-06-10

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

### `SimpleNamespace` — 경량 가짜 객체
- `from types import SimpleNamespace`로 임포트. 동적으로 속성을 붙일 수 있는 빈 객체.
- `obj = SimpleNamespace(a=1, b=2)` → `obj.a == 1`
- Fake 클래스를 따로 선언하지 않고 단순한 구조체가 필요할 때 사용한다.
- 예: `request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=db)))`
- `type()` 동적 클래스 생성과 비슷하지만, 중첩 구조를 표현하기 더 자연스럽다.
- 파일: `backendPython/tests/unit/test_dependencies.py`

### `getattr(obj, key, default)` — 안전한 속성 접근
- `obj.key`는 속성이 없으면 `AttributeError`를 발생시킨다.
- `getattr(obj, "key", None)`은 속성이 없으면 `None`을 반환한다.
- 런타임에 속성 존재 여부가 불확실한 경우(예: `app.state.database` 미설정)에 사용한다.
- 파일: `backendPython/app/api/dependencies.py`
