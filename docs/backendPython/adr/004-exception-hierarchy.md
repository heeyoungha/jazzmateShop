# ADR-BP004: 예외 계층 설계와 래핑 정책

## Context

FastAPI 추천 서버는 임베딩 생성, 유사도 검색, 추천 사유 생성, Spring 콜백 전송 등 여러 외부 I/O를 거친다.
각 단계에서 발생하는 예외는 Python 내장 예외(`ConnectionError`, `TimeoutError`, `ValueError` 등)부터 OpenAI SDK 예외, httpx 예외까지 다양하다.

호출자(서비스 레이어, 라우터)가 각 외부 라이브러리의 예외 타입을 직접 의존하면 외부 라이브러리 교체 시 예외 처리 코드가 연쇄 변경된다.
또한 예외 원인이 사라지면 디버깅이 어려워진다.

---

## Decision 1: 도메인 예외 계층을 별도 모듈로 관리한다

모든 도메인 예외는 `app/core/exceptions.py`에 정의한다.

```
Exception                    (Python 내장)
 └── RecommendationError     (도메인 최상위)
      ├── ConfigurationError
      ├── EmbeddingError
      └── RepositoryError
      └── CallbackError
```

| 예외 클래스 | 발생 조건 |
|---|---|
| `RecommendationError` | 모든 도메인 예외의 기반, 직접 raise하지 않음 |
| `ConfigurationError` | 설정값 누락 또는 유효하지 않은 설정 |
| `EmbeddingError` | OpenAI 임베딩 생성 실패 |
| `RepositoryError` | DB 유사도 검색 실패 |
| `CallbackError` | Spring 콜백 전송 실패 (4xx/5xx, timeout) |

---

## Decision 2: 외부 예외는 경계에서 도메인 예외로 래핑한다

각 클라이언트/레포지토리는 외부 라이브러리 예외를 직접 노출하지 않고, 경계(boundary)에서 대응하는 도메인 예외로 변환한다.

```python
except CallbackError:
    raise
except Exception as exc:
    raise CallbackError(str(exc)) from exc
```

- 이미 도메인 예외(`CallbackError`)이면 그대로 다시 던진다.
- 그 외 예외(`ConnectionError`, `TimeoutError` 등)는 `CallbackError`로 래핑한다.
- `from exc`로 원인 체인을 보존해 스택 트레이스에서 원래 예외를 확인할 수 있게 한다.

`except CallbackError`를 먼저 선언하는 이유: `CallbackError`는 `Exception`의 하위 클래스이므로 순서가 바뀌면 두 번째 블록에서 잡혀 이중 래핑된다.

---

## Decision 3: `from exc`로 예외 원인 체인을 보존한다

`raise DomainError(...) from exc`는 Python의 명시적 예외 체인(PEP 3134)을 사용한다.

- 스택 트레이스에 "The above exception was the direct cause of the following exception" 메시지와 함께 원래 예외가 출력된다.
- 원인이 제거되지 않으므로 운영 로그에서 근본 원인(root cause)을 추적할 수 있다.
- `from None`은 원인을 숨기므로 이 프로젝트에서 사용하지 않는다.

---

## Rationale

**도메인 예외로 래핑하는 이유**

- 서비스 레이어가 `httpx.TimeoutException`, `openai.APIError` 등 외부 라이브러리 타입을 `except`할 필요가 없다.
- 외부 라이브러리를 교체해도 클라이언트 경계의 래핑 코드만 수정하면 서비스/라우터 레이어는 변경하지 않아도 된다.
- `RecommendationError`를 기반 타입으로 두면 라우터에서 도메인 예외 전체를 한 번에 처리할 수 있다.

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| 외부 예외를 그대로 노출 | 기각 | 호출자가 외부 라이브러리에 직접 의존해 교체 비용이 증가한다. |
| 단일 예외 클래스로 모든 실패 처리 | 기각 | 실패 원인을 타입으로 구분할 수 없어 라우터의 에러 코드 매핑이 어려워진다. |
| 도메인 예외 계층 분리 (채택) | 채택 | 실패 원인을 타입으로 구분하고, 외부 의존을 경계에서 차단한다. |

---

## Consequences

- 각 클라이언트/레포지토리는 `try/except` 래핑 책임을 진다.
- 서비스 레이어는 도메인 예외 타입만 처리하면 된다.
- 새로운 외부 I/O 단계가 추가되면 대응하는 도메인 예외 클래스를 `exceptions.py`에 추가하고 이 ADR을 개정한다.
- `from exc` 없이 래핑하면 원인 체인이 끊기므로 반드시 `from exc`를 사용한다.
