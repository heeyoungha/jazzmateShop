# ADR-BP001: FastAPI 모듈/레이어 설계 결정

## Context

Python 백엔드는 Spring Boot가 저장한 감상문을 입력으로 받아 AI 추천을 처리한다.

역할은 작지만 외부 의존성이 많다.

- OpenAI Embeddings API
- OpenAI Chat API
- Supabase/PostgreSQL `v_embedding_with_album`
- Spring Boot 콜백 API

Router, 추천 정책, DB 조회, 외부 HTTP 호출이 섞이면 테스트가 어려워지고 실패 지점을 분리하기 어렵다.

---

## Decision 1: Router는 202 응답과 작업 등록만 담당한다

`POST /recommend/by-review` Router는 요청 검증 후 추천 처리를 백그라운드 작업으로 넘기고 `202 Accepted`를 반환한다.

Router는 다음 작업을 직접 수행하지 않는다.

- OpenAI 호출
- Supabase 조회
- 추천 사유 생성
- Spring Boot 콜백 전송

### Rationale

`POST /recommend/by-review`는 Spring Boot가 감상문 저장 트랜잭션 커밋 후 비동기로 호출하는 시작 신호다.
Spring은 이 응답 body를 비즈니스 데이터로 사용하지 않고, FastAPI 처리 결과는 별도 콜백으로 받는다.

따라서 Router가 OpenAI/DB 작업이 끝날 때까지 요청을 붙잡으면 다음 문제가 생긴다.

- Spring의 외부 HTTP 호출 시간이 OpenAI와 DB 지연 시간에 직접 묶인다.
- 추천 처리 실패와 HTTP 요청 실패의 경계가 흐려진다.
- Controller/Router 테스트가 외부 API mock까지 알아야 한다.
- `202 Accepted` 계약과 실제 처리 완료 계약이 섞인다.

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| Router에서 전체 추천 처리를 동기 실행 | 기각 | 구현은 단순하지만 Spring 호출 timeout, OpenAI 지연, 콜백 실패가 하나의 HTTP 요청에 묶인다. |
| Router는 202만 반환하고 background task 등록 | 채택 | API 계약이 "처리 시작 수락"임을 명확히 하고, 실제 완료는 콜백으로 분리한다. |
| 메시지 큐 기반 worker 분리 | 보류 | 운영 안정성은 높지만 현재 범위에는 Redis/Celery 같은 추가 인프라와 재처리 정책이 필요하다. |

---

## Decision 2: Service가 추천 유스케이스를 조합한다

추천 처리 순서는 `RecommendationService`가 조합한다.

```text
recommend_router
  -> recommendation_service.recommend_by_review()
    -> embedding_service.embed_review()
    -> album_embedding_repository.find_similar_albums()
    -> recommendation_reason_service.generate_reasons()
    -> spring_callback_client.send_recommendations()
```

Service는 FastAPI Request/Response 객체에 의존하지 않는다.

### Rationale

추천 처리는 여러 하위 작업을 순서대로 조합하는 유스케이스다.

- 사용자 감상문 임베딩 생성
- 앨범 후보 검색
- 추천 사유 생성
- Spring 콜백 전송

이 순서를 Router에 두면 HTTP 계층이 비즈니스 흐름을 알게 되고, 각 실패 지점별 테스트가 복잡해진다.
반대로 각 하위 서비스가 다음 단계를 직접 호출하면 흐름이 분산되어 "추천 요청 하나가 어떤 순서로 완료되는지"를 한 곳에서 파악하기 어렵다.

`RecommendationService`를 유스케이스 조합 계층으로 두면 Router는 얇게 유지되고, Service 테스트에서 하위 의존성을 mock으로 대체해 성공/실패 분기를 직접 검증할 수 있다.

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| Router가 모든 하위 서비스를 직접 호출 | 기각 | HTTP 계층과 추천 유스케이스가 결합되고 Router 테스트 범위가 커진다. |
| 각 서비스가 다음 서비스를 연쇄 호출 | 기각 | 흐름이 분산되어 실패 처리와 순서 검증이 어렵다. |
| `RecommendationService`가 유스케이스를 조합 | 채택 | 추천 처리 순서, 정책, 실패 분기를 한 곳에서 테스트할 수 있다. |

---

## Decision 3: Repository는 `v_embedding_with_album` 읽기 전용 조회만 담당한다

FastAPI의 DB 접근은 추천 후보 검색으로 제한한다.

- 검색 대상은 `v_embedding_with_album`으로 고정한다.
- `user_reviews`, `recommend_album`을 직접 변경하지 않는다.
- 추천 결과 저장과 `recommendationStatus` 전이는 Spring Boot 콜백 API에 위임한다.

현재 DB 뷰가 임베딩 벡터 컬럼을 노출하지 않는 환경에서는 구현 전에 별도 마이그레이션을 수동 적용해야 한다.
Python 구현에서 `embedding_vectors`를 직접 우회 조회하지 않는다.

### Rationale

이 프로젝트에서 추천 상태의 source of truth는 Spring Boot와 PostgreSQL의 `user_reviews.recommendation_status`다.
FastAPI가 `recommend_album` 저장이나 상태 전이를 직접 수행하면 Spring의 콜백 저장 로직, 중복 처리, 상태 전이 정책과 충돌할 수 있다.

`v_embedding_with_album`은 추천 검색을 위한 읽기 모델이다.
FastAPI가 이 뷰만 조회하면 "조인 쿼리를 안 써서 단순하다" 이상의 이점이 있다.

1. 스키마 변경 격리
   - 추천 후보는 `embedding_vectors`, 리뷰 원문/요약, 앨범 메타데이터, URL 같은 파이프라인 산출물을 함께 필요로 한다.
   - FastAPI가 원천 테이블을 직접 조인하면 파이프라인 내부 스키마 변경이 곧바로 FastAPI 장애로 이어진다.
   - View를 계약으로 두면 내부 테이블 조인 방식이 바뀌어도 `v_embedding_with_album`의 컬럼 계약만 유지하면 FastAPI 코드는 유지된다.

2. 권한과 쓰기 경계 축소
   - FastAPI는 추천 검색에 필요한 읽기 권한만 가지면 된다.
   - `recommend_album`, `user_reviews`, 파이프라인 원천 테이블에 대한 직접 쓰기/넓은 읽기 권한을 줄일 수 있다.
   - 이는 "추천 계산 서버"가 "상태 저장 서버"가 되는 일을 막는다.

3. 쿼리 성능과 인덱스 설계 위치 고정
   - pgvector similarity search, 필요한 조인, 필터링 조건을 DB View 또는 View 뒤의 DB 설계에서 관리할 수 있다.
   - FastAPI 코드 여러 곳에 유사한 조인/정렬 조건이 흩어지는 일을 막고, 성능 튜닝 지점을 DB 계약 하나로 모은다.

4. 테스트와 mock 단순화
   - Repository 테스트는 `v_embedding_with_album`의 입력/출력 row 계약만 검증하면 된다.
   - 여러 원천 테이블 fixture를 매번 구성하지 않아도 되어 추천 서비스 테스트가 가벼워진다.

5. 도메인 언어 정리
   - FastAPI는 "embedding row", "raw review row"가 아니라 "추천 가능한 앨범 후보"를 다룬다.
   - View 이름과 컬럼이 추천 도메인의 읽기 모델 역할을 하므로 서비스 코드가 파이프라인 구현 세부사항에 덜 오염된다.

`embedding_vectors` 직접 조회를 허용하지 않는 이유는 우회 조회가 생기면 `v_embedding_with_album`이 제공하는 앨범 식별자, 제목 파싱, URL 조인 계약이 무력화되기 때문이다.
뷰 스키마가 부족하면 우회가 아니라 뷰 계약을 먼저 수정해야 한다.

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| FastAPI가 `embedding_vectors` 등 원천 테이블 직접 조회 | 기각 | pipeline 내부 스키마와 강하게 결합되고, 앨범 메타데이터 조인 규칙이 코드에 흩어진다. |
| FastAPI가 `recommend_album` 직접 저장 | 기각 | Spring의 콜백 저장, UNIQUE 처리, 상태 전이 책임과 충돌한다. |
| FastAPI는 `v_embedding_with_album`만 읽고 결과는 Spring 콜백 | 채택 | 읽기 모델과 쓰기 모델의 책임이 분리되고 API 계약이 단순해진다. |

---

## Decision 4: 초기 패키지 구조

초기 구현 기준 구조는 다음과 같다.

```text
backendPython/
  app/
    main.py
    api/
      recommend_router.py
    core/
      config.py
      logging.py
      exceptions.py
    schemas/
      recommendation.py
    services/
      recommendation_service.py
      embedding_service.py
      recommendation_reason_service.py
    repositories/
      album_embedding_repository.py
    clients/
      openai_client.py
      spring_callback_client.py
  tests/
    unit/
    integration/
```

### Rationale

초기 구조는 "추천 서버가 지금 가진 책임"에 맞춰 최소 레이어만 둔다.

- `api`: HTTP entrypoint
- `services`: 추천 유스케이스와 AI 처리
- `repositories`: DB 읽기 모델 조회
- `clients`: 외부 HTTP/API 통신
- `schemas`: 경계 DTO
- `core`: 설정, 로깅, 예외

도메인 모델이나 복잡한 command/query 패키지를 별도로 두지 않는 이유는 현재 FastAPI가 자체 도메인 상태를 소유하지 않기 때문이다.
추천 상태와 저장 도메인은 Spring Boot가 소유하고, Python은 계산과 콜백을 담당한다.

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| 단일 파일 또는 router 중심 구조 | 기각 | 초기 구현은 빠르지만 OpenAI/DB/Spring mock 테스트가 어려워진다. |
| Java식 Controller-Service-Repository를 그대로 복제 | 부분 채택 | 레이어 분리는 유용하지만 FastAPI의 외부 client와 schema 경계를 명시해야 한다. |
| Clean Architecture식 usecase/domain/gateway 세분화 | 보류 | 현재 범위에 비해 구조가 무겁고, Python 서버가 도메인 상태를 소유하지 않는다. |
| `api/services/repositories/clients/schemas/core` 구조 | 채택 | 현재 책임을 분리하면서도 과도한 추상화를 피한다. |

---

## Consequences

- Router 테스트는 HTTP 계약과 background task 등록에 집중한다.
- Service 테스트는 OpenAI, DB, Spring 클라이언트를 mock으로 교체해 추천 흐름을 검증한다.
- DB 상태 변경 책임이 Spring Boot에 유지되어 추천 상태 모델이 단순해진다.
- `v_embedding_with_album` 뷰 스키마가 추천 검색 요구사항과 맞지 않으면 구현보다 DB 설계 문서를 먼저 갱신해야 한다.
- background task가 프로세스 장애 시 유실될 수 있으므로, 운영에서 유실 허용이 어려워지면 queue/worker ADR을 별도로 작성해야 한다.
- 레이어가 분리되는 만큼 작은 클래스와 파일이 늘어나지만, 외부 의존성 mock 테스트 비용은 줄어든다.
