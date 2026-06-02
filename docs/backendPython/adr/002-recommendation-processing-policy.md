# ADR-BP002: 추천 처리와 콜백 정책 결정

## Context

FastAPI 추천 서버는 Spring Boot로부터 감상문 본문을 받아 앨범 추천을 계산한다.

공통 API 계약은 다음 흐름을 요구한다.

```text
Spring Boot -> POST /recommend/by-review -> FastAPI
FastAPI -> POST /api/user-reviews/{reviewId}/recommendations -> Spring Boot
```

추천 결과 저장과 `recommendationStatus` 전이는 Spring Boot가 담당한다.

---

## Decision 1: 추천 수는 설정값 하나로 관리한다

추천 수는 `RECOMMENDATION_TOP_K`로 관리한다.

- 기본값: `3`
- 변경 시 서비스 로직이 아니라 설정값만 수정한다.
- `COMPLETED` 콜백 payload의 `recommendations` 길이는 이 값을 초과하지 않는다.

---

## Decision 2: 임베딩 모델과 추천 사유 모델을 설정으로 분리한다

기본 모델:

| 용도 | 설정 | 기본값 |
|---|---|---|
| 사용자 감상문 임베딩 | `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` |
| 추천 사유 생성 | `OPENAI_CHAT_MODEL` | `gpt-4o-mini` |

모델명은 코드에 하드코딩하지 않고 `core/config.py`에서 관리한다.

임베딩 생성과 추천 사유 생성은 OpenAI Python SDK 직접 사용을 기본으로 한다.
LangChain은 프롬프트 체인, output parser, retriever 연결 등 모델 호출 주변 복잡도가 실제로 커질 때 도입한다.

### Rationale

기존 `backend/ai-service/services/recommendation_reason_service.py`는 LangChain `ChatOpenAI`와 `ChatPromptTemplate`를 사용해 추천 사유 프롬프트를 구조화했다.
이 구현에서 배울 점은 LangChain 자체보다 system/human message 분리, prompt 변수 주입, async 호출, timeout/retry 정책을 한 곳에 모은 패턴이다.

현재 목표는 Embeddings API 호출, 단일 Chat API 호출, 간단한 prompt 구성, fallback 생성이다.
이 범위에서는 LangChain이 제공하는 chain/retriever/tool 추상화가 필요하지 않으므로 OpenAI SDK 직접 사용이 더 단순하다.
프롬프트 템플릿은 프로젝트 코드의 작은 함수나 Pydantic DTO로 관리한다.

채택할 부분:

- system/human message 분리
- prompt 변수 주입 위치 고정
- OpenAI async client 기반 비동기 임베딩 생성
- OpenAI async client 기반 비동기 추천 사유 생성
- LLM timeout과 max retries 설정
- 후보별 추천 사유 병렬 생성

그대로 가져오지 않을 부분:

- 현재 단계에서 LangChain 의존성 추가
- 모델명 하드코딩
- `os.getenv()` 직접 접근
- 서비스 내부에서 pickle 실패 저장 파일 관리
- track 중심 필드명

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| HTTP API 직접 호출 | 기각 | 의존성은 적지만 요청/응답, 에러 매핑, retry, timeout, API 스펙 변경 대응을 직접 관리해야 한다. |
| OpenAI Python SDK 직접 사용 | 채택 | 공식 SDK가 인증, 요청/응답 타입, async client, timeout/retry 설정을 제공하면서도 구조가 단순하다. |
| LangChain `ChatOpenAI` 사용 | 보류 | 프롬프트 체인, output parser, retrieval chain이 필요해질 때 가치가 커진다. 현재 단일 호출에는 과하다. |
| 현재 코드처럼 LangChain 설정을 서비스 내부에 하드코딩 | 기각 | 모델 교체와 테스트가 어렵고 `core/config.py` 원칙과 충돌한다. |

---

## Decision 3: 유사도 검색 대상은 `v_embedding_with_album`으로 고정한다

추천 후보 검색은 `v_embedding_with_album`을 기준으로 수행한다.

이 View는 FastAPI가 여러 파이프라인 원천 테이블을 직접 조인하지 않도록 만든 추천 검색용 읽기 모델이다.
FastAPI는 "추천 가능한 앨범 후보"라는 계약만 소비하고, 원천 테이블 조인 방식과 pipeline 내부 스키마는 DB/View 계층에 숨긴다.

필요 컬럼:

| 컬럼 | 설명 |
|---|---|
| `album_id` | Spring 콜백의 `albumId` (UUID 문자열) |
| `album_artist` | 추천 사유 생성 컨텍스트 |
| `album_title` | 추천 사유 생성 컨텍스트 |
| `url` | 선택적 컨텍스트 또는 디버깅 정보 |
| `embedding` | pgvector 유사도 계산 대상 |

정렬 기준:

```text
cosine similarity DESC
LIMIT RECOMMENDATION_TOP_K
```

추천 점수는 Spring DB 제약에 맞춰 `0.0000`부터 `1.0000` 사이 값으로 정규화하고 소수점 4자리까지 전달한다.

### Rationale

`v_embedding_with_album`을 고정 검색 대상으로 두면 다음 이점이 있다.

- FastAPI가 `embedding_vectors`, 리뷰 원문, 요약, URL 테이블의 조인 구조를 알 필요가 없다.
- pipeline 내부 테이블이 바뀌어도 View 컬럼 계약만 유지하면 FastAPI 변경을 줄일 수 있다.
- DB 권한을 추천 후보 View 읽기로 제한할 수 있어 상태 테이블에 대한 우발적 접근을 줄인다.
- pgvector 검색/필터링/정렬 튜닝 지점을 DB View 계약 근처에 모을 수 있다.
- 테스트에서 여러 테이블 fixture 대신 View row fixture만 준비하면 된다.

---

## Decision 4: 추천 사유는 후보 앨범과 1:1로 생성한다

`recommendation_reason_service`는 사용자 감상문과 TOP K 앨범 메타데이터를 입력으로 받아 앨범별 추천 사유를 생성한다.

- 출력은 검색 결과의 `album_id`와 1:1로 매칭되어야 한다.
- 추천 사유는 Spring 콜백 DTO의 `recommendationReason`에 들어갈 짧은 한국어 문장으로 제한한다.
- 후보 목록이 비어 있으면 OpenAI Chat API를 호출하지 않는다.
- 여러 후보의 추천 사유는 `asyncio.gather()` 등으로 병렬 생성할 수 있다.
- 프롬프트에는 사용자 감상문, 앨범 아티스트/제목, 전문가 리뷰 원문 일부, GPT 요약 일부를 포함할 수 있다.

### Rationale

기존 구현은 후보별 LLM 호출을 병렬화해 추천 사유 생성 지연을 줄였다.
TOP K가 작더라도 각 LLM 호출은 네트워크 I/O이므로 순차 실행보다 병렬 실행이 사용자 대기 시간을 줄인다.

또한 추천 사유에 전문가 리뷰 원문과 요약을 함께 넣으면 단순히 "유사합니다" 수준의 문구보다 앨범의 실제 음악적 특징을 반영하기 쉽다.
단, prompt 입력은 길이를 제한해 비용과 latency를 통제한다.

---

## Decision 5: 성공/실패 모두 같은 콜백 API로 처리 결과를 전송한다

`SpringCallbackClient`는 다음 API로 추천 처리 결과를 전달한다.

```text
POST {SPRING_BASE_URL}/api/user-reviews/{reviewId}/recommendations
```

성공 콜백 payload:

```json
{
  "status": "COMPLETED",
  "recommendations": [
    {
      "albumId": "00000000-0000-0000-0000-000000000101",
      "recommendationScore": 0.9423,
      "recommendationReason": "모달 재즈 특유의 정적인 분위기가 유사합니다."
    }
  ]
}
```

실패 콜백 payload:

```json
{
  "status": "FAILED",
  "errorCode": "NO_CANDIDATES",
  "message": "추천 후보가 없습니다.",
  "recommendations": []
}
```

- 2xx 응답이면 성공으로 처리한다.
- 응답 body는 파싱하지 않는다.
- 콜백 실패 재시도 정책은 별도 결정 전까지 자동 재시도하지 않는다.

비동기 추천 처리에서는 `202 Accepted` 이후 Spring이 결과를 알 수 있는 경로가 콜백뿐이다.
따라서 임베딩 실패, 유사도 검색 실패, 후보 0건 같은 terminal failure도 기존 콜백 API에 `status=FAILED`로 전송한다.

---

## Decision 6: 추천 사유 생성 실패 시 fallback 사유를 사용한다

추천 사유 생성 LLM 호출이 실패하거나 빈 응답을 반환하면 전체 추천을 실패시키지 않고 fallback 사유를 생성한다.

Fallback 사유는 다음 입력만 사용한다.

- 사용자 감상문에서 추출한 음악 키워드
- 후보 앨범의 리뷰 원문/요약에서 추출한 음악 특징
- 앨범 아티스트와 제목
- 유사도 점수

Fallback 결과도 Spring 콜백의 `recommendationReason`에 들어갈 완전한 한국어 문장이어야 한다.

### Rationale

기존 `RecommendationReasonService`는 LLM 실패 시 키워드 기반 fallback 문장을 생성한다.
추천 후보 검색이 이미 성공한 상황에서 추천 사유 생성만 실패했다고 전체 콜백을 중단하면 사용자는 추천 결과를 받지 못한다.

현재 서비스 목표에서는 "완벽한 사유"보다 "추천 결과를 안정적으로 완료하는 것"이 더 중요하다.
따라서 LLM 실패는 추천 전체 실패가 아니라 사유 품질 저하로 처리한다.

### Alternatives

| 옵션 | 채택 여부 | 이유 |
|---|---|---|
| 추천 사유 실패 시 전체 추천 실패 | 기각 | 후보 검색은 성공했는데 사용자에게 아무 결과도 제공하지 못한다. |
| fallback 사유 사용 | 채택 | 추천 완료율을 높이고 Spring 콜백 계약을 유지한다. |
| 실패 데이터를 로컬 pickle로 저장 후 수동 재시도 | 기각 | 컨테이너 환경에서 파일 영속성이 약하고 운영 관측 지점이 분산된다. 필요하면 DB/로그 기반 재처리 ADR로 별도 설계한다. |

---

## Decision 7: 실패 상태 전이는 Spring Boot 책임이다

FastAPI는 실패 시 DB 상태를 직접 변경하지 않는다.

| 실패 지점 | 처리 |
|---|---|
| 요청 검증 실패 | FastAPI 422 |
| OpenAI 임베딩 실패 | `status=FAILED` 콜백 전송 |
| 유사도 검색 실패 | `status=FAILED` 콜백 전송 |
| 추천 후보 0건 | 실패로 간주, `status=FAILED` 콜백 전송 |
| 추천 사유 생성 실패 | fallback 사유로 콜백 진행 |
| Spring 콜백 전송 실패 | 별도 결정 전까지 로그만 기록, 자동 재시도 없음 |

Spring의 `FAILED` 전이 정책과 retry API가 최종 사용자 흐름을 관리한다.

추천 후보 0건은 정상적인 "빈 추천 결과"가 아니라 데이터 준비, View 정의, 권한, 필터링, 임베딩 차원 불일치 같은 검색 준비 상태 이상으로 본다.
단순 TOP K 검색은 유사도가 낮아도 후보가 있으면 결과를 반환해야 하므로, 0건은 실패로 기록한다.

---

## Deferred Decisions

아래 정책은 구현 전에 확정한다.

| 정책 | 선택지 |
|---|---|
| Spring 콜백 전송 실패 | 로그만 기록 또는 제한적 재시도 |
| similarity score 기준 | min score 미만 제외 여부 |

---

## Consequences

- Spring-FastAPI 계약이 callback payload 중심으로 단순해진다.
- 추천 상태 관리가 Spring Boot 한 곳에 남는다.
- 콜백 실패 자동 재시도가 없으므로 운영 단계에서 실패 관측과 재처리 정책을 별도로 설계해야 한다.
- 추천 사유 생성은 OpenAI SDK 직접 사용을 기본으로 하므로 초기 의존성이 작고 테스트가 단순하다.
- LangChain 도입이 필요해지면 별도 ADR 또는 ADR-BP002 개정으로 도입 근거와 대체 비용을 기록한다.
- LLM 실패 시 fallback을 사용하므로 추천 완료율은 높아지지만 추천 사유 품질이 낮아질 수 있다.
- 후보 0건은 실패로 간주하므로, 데이터 파이프라인/View/권한 이상을 조기에 드러낼 수 있다.
