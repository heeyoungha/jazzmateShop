# Python 백엔드 규칙

> 적용 범위: `backendPython/` 디렉터리 (FastAPI AI 추천 서버)
> 공통 규칙: [루트 AGENTS.md](../AGENTS.md)
> 설계 문서: [docs/backendPython/SDD.md](../docs/backendPython/SDD.md)

---

## 역할

FastAPI 서버는 Spring Boot가 저장한 사용자 감상문을 입력으로 받아 앨범 추천을 비동기로 처리한다.

처리 결과는 직접 DB에 저장하지 않고 Spring Boot 콜백 API로 전달한다.

---

## 설계 기준

구현 변경 시 아래 문서를 우선 확인한다.

| 문서 | 언제 확인할지 |
|---|---|
| [docs/SDD.md](../docs/SDD.md) | 공통 라우팅, 추천 상태 전이 변경 시 |
| [docs/API_SPEC.md](../docs/API_SPEC.md) | Spring-FastAPI API 계약 변경 시 |
| [docs/backendPython/SDD.md](../docs/backendPython/SDD.md) | Python 백엔드 역할, 플로우 링크 확인 시 |
| [docs/backendPython/flows/](../docs/backendPython/flows/) | 플로우별 구현 상세 또는 테스트 시나리오 변경 시 |
| [ADR-BP001](../docs/backendPython/adr/001-fastapi-module-design.md) | FastAPI 모듈/레이어 구조 변경 시 |
| [ADR-BP002](../docs/backendPython/adr/002-recommendation-processing-policy.md) | 추천 검색, 콜백, 실패 처리 정책 변경 시 |
| [ADR-BP003](../docs/backendPython/adr/003-test-strategy.md) | Python 테스트 전략 변경 시 |
| [ADR-004](../docs/pipeline/adr/004-db-schema-and-state-model.md) | `v_embedding_with_album`, 임베딩 테이블 관련 변경 시 |

---

## 구현 원칙

- FastAPI의 DB 접근은 추천 검색용 읽기 모델인 `v_embedding_with_album` 조회로 제한한다.
- 추천 결과 저장과 `recommendationStatus` 전이는 Spring Boot 콜백 API에 위임한다.
- 브라우저가 FastAPI를 직접 호출하는 API를 만들지 않는다.
- 환경변수는 설정 모듈에서 중앙 관리하고, `.env` 파일은 직접 수정하지 않는다.
- 코드에 API 키, URL, 모델명 정책 값을 하드코딩하지 않는다.
- 외부 API/DB 경계 데이터는 Pydantic 모델로 검증한다.
- 공개 함수와 서비스 메서드는 타입 힌트와 반환 타입을 명시한다.
- 비동기 I/O는 `async/await` 흐름을 유지한다.

---

## 테스트 원칙

- 테스트 코드를 먼저 작성하고 구현한다.
- OpenAI, Supabase, Spring Boot는 기본적으로 mock/fake로 격리한다.
- 실제 네트워크 호출이 필요한 테스트는 별도 integration marker를 붙이고 기본 테스트 실행에서 제외한다.
- 테스트 시나리오는 [docs/backendPython/flows/](../docs/backendPython/flows/)의 각 플로우 문서를 기준으로 작성한다.

### 레이어별 검증 책임

각 테스트 파일은 자신의 레이어 책임만 검증한다. 다른 레이어의 책임을 중복 검증하지 않는다.

| 레이어 | 파일 패턴 | 검증 대상 |
|---|---|---|
| DTO | `test_*_dto.py` | 필수값, 타입, 값 범위, trim·공백 |
| Router | `test_*_router.py` | HTTP 상태코드, service 위임 여부 |
| Service | `test_*_service.py` | 유스케이스 분기, 처리 흐름 |
| Client/Repository | `test_*_client.py`, `test_*_repository.py` | 외부 API 통신 포맷, 직렬화 |
