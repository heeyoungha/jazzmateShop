# 추천 E2E k6 결과

## 문서 위치와 기록 원칙

- 상세 결과/명령/해석: `load-tests/recommendation-e2e-results.md`
- k6 raw summary: `load-tests/*summary.json`
- Grafana/Prometheus 캡처: `load-tests/monitoring/`

`docs/고도화.md`에는 결론과 링크만 남기고, 실행 명령/표/로그 해석은 이 문서에 누적한다.

## 측정 맥락

- 대상 흐름: `POST /api/user-reviews` -> `GET /api/user-reviews/{id}` polling -> terminal status 확인
- 종료 상태: `COMPLETED`, `FAILED`, `MAX_WAIT_SECONDS` 초과 timeout
- 목적: 감상문 제출부터 추천 완료 확인까지의 end-to-end 지연 시간을 측정한다.

---

## 개인화/클러스터링 적용 후 측정

MusicBrainz 메타 재순위와 개인화 클러스터링 로직이 붙은 뒤, SSE 전환 필요성을 판단하기 위해 측정했다.

### 측정 모드 구분

| 모드 | FastAPI 앱 | OpenAI | 추천 DB 조회 | Spring 저장 DB | 목적 |
|---|---|---|---|---|---|
| Mock AI E2E | mock FastAPI | mock | 사용 안 함 | local PostgreSQL | Spring submit/callback/polling 구조 한계 확인 |
| Real FastAPI E2E | 실제 `app.main:app` | real | 실제 Supabase | local PostgreSQL | 실제 외부 API 포함 소량 smoke |
| DB Real + OpenAI Mock | 실제 `app.main:app` | mock | 실제 Supabase | local PostgreSQL | GPT 비용 제거 후 실제 추천 DB 조회 경로의 고동시성 한계 확인 |

**모드별 스택 차이가 결과 해석에 중요하다.**

Mock AI E2E는 embedding 생성, Supabase pgvector 검색, 개인화 클러스터링을 전혀 실행하지 않는다. 지연 시간만 시뮬레이션하고 고정 응답을 callback으로 보내는 단순한 mock 서버다. 따라서 500 VU에서 22,000건 이상이 전부 완료된 것은 "실제 추천 파이프라인이 500 VU를 버틴다"는 근거가 아니다. Spring submit/callback/polling 구조 자체의 처리 여력을 확인한 것이다.

DB Real + OpenAI Mock은 실제 FastAPI가 Supabase pgvector 검색, 메타데이터 재순위, 클러스터링을 전부 실행한다. 추천 1건당 처리 비용이 Mock AI와 비교할 수 없이 크기 때문에, 같은 VU 수에서도 유입 속도를 따라가지 못하고 PENDING이 쌓이기 시작한다.

### 사용한 파일

```text
load-tests/recommendation-e2e.js
load-tests/docker-compose.recommendation-real.yml
load-tests/docker-compose.recommendation-db-real-openai-mock.yml
backendPython/app/main.py
backendPython/app/core/config.py
```

`recommendation-e2e.js`는 `REVIEW_POOL_SIZE=1000` 기본값으로 1000개 감상문 mock pool을 순환한다. 감상문 생성은 외부 API를 호출하지 않는다.

`MOCK_OPENAI=true`일 때 FastAPI는 실제 서비스/Repository/Rerank 경로를 사용하되, OpenAI embedding/chat client만 fake client로 대체한다. 따라서 DB Real + OpenAI Mock 테스트는 GPT 비용 없이 실제 Supabase 조회 경로를 압박한다.

### Real FastAPI E2E 소량 측정

실제 FastAPI와 실제 OpenAI/Supabase를 모두 사용했다. 비용과 rate limit 위험 때문에 1/5/10 VU, 30초로 제한했다.

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
VUS=10 \
DURATION=30s \
k6 run --summary-export=load-tests/recommendation-real-10vu-summary.json \
load-tests/recommendation-e2e.js
```

| VU | duration | submitted | completed | success rate | submit p95 | polling p95 | time_to_completed p95 | timeout |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30s | 6 | 6 | 100% | 214.57 ms | 88.30 ms | 10.86 s | 0 |
| 5 | 30s | 36 | 36 | 100% | 18.59 ms | 14.23 ms | 6.80 s | 0 |
| 10 | 30s | 51 | 51 | 100% | 30.18 ms | 17.96 ms | 6.05 s | 0 |

해석:

- 실제 FastAPI/OpenAI/Supabase 경로는 10 VU 소량 부하까지 실패 없이 완료됐다.
- submit/polling API 자체는 낮은 지연을 유지했다.
- 추천 완료 p95는 약 6초 수준이었다.
- 이 결과만으로는 polling이 병목이라고 볼 근거가 없다.

### DB Real + OpenAI Mock 1000 VU 측정

이 테스트는 GPT API만 mock하고, FastAPI의 실제 추천 서비스/Repository/Rerank 경로와 실제 Supabase DB 조회를 사용했다.

실행 전 1 VU smoke:

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
REVIEW_POOL_SIZE=1000 \
VUS=1 \
DURATION=15s \
k6 run --summary-export=load-tests/recommendation-db-real-openai-mock-1vu-summary.json \
load-tests/recommendation-e2e.js
```

1 VU smoke 결과:

| VU | duration | submitted | completed | success rate | submit p95 | polling p95 | time_to_completed p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 15s | 5 | 5 | 100% | 236.28 ms | 104.02 ms | 3.34 s |

1000 VU ramping:

```bash
BASE_URL=http://localhost:18080 \
REQUEST_TIMEOUT=60s \
POLLING_INTERVAL_SECONDS=3 \
MAX_WAIT_SECONDS=180 \
REVIEW_POOL_SIZE=1000 \
LOAD_PROFILE=ramping \
RAMP_UP_DURATION=1m \
RAMP_UP_VUS=500 \
HOLD_DURATION=1m \
HOLD_VUS=1000 \
RAMP_DOWN_DURATION=30s \
k6 run --summary-export=load-tests/recommendation-db-real-openai-mock-1000vu-summary.json \
load-tests/recommendation-e2e.js
```

1000 VU 결과:

| 항목 | 값 |
|---|---:|
| submitted_reviews | 1,374 |
| completed_reviews | 374 |
| completion coverage | 27.2% |
| interrupted iterations | 1,000 |
| pending_responses | 34,067 |
| polling_count_per_review p95 | 13 |
| submit p95 | 10.40 ms |
| polling p95 | 5.20 ms |
| time_to_completed p95 | 39.05 s |
| time_to_completed max | 48.06 s |
| HTTP failure rate | 0% |

주의:

- k6의 `completion_success_rate=100%`는 terminal result까지 도달한 374건 안에서 실패가 없었다는 뜻이다.
- 전체 제출 1,374건 중 완료된 것은 374건뿐이므로, 핵심 지표는 `completion coverage=27.2%`, `interrupted iterations=1,000`, `PENDING 누적`이다.

테스트 종료 직후 local Spring DB 상태:

```text
COMPLETED: 446
PENDING:   1,933
```

이 값에는 사전 seed 데이터와 1 VU smoke 결과가 함께 포함되어 있다. 핵심은 테스트 종료 뒤에도 `PENDING`이 대량으로 남았다는 점이다.

FastAPI 로그에서 확인된 오류:

```text
httpx.ConnectTimeout
app.core.exceptions.CallbackError
Spring callback failed
```

Grafana 캡처: `load-tests/monitoring/개인화클러스터링/스크린샷 2026-06-28 오후 9.53.37.png`

| 패널 | 관측 |
|---|---|
| Completion Coverage | 21:45부터 28%로 급락 후 수평 — 제출은 계속 들어오는데 완료가 멈춘 시점이 명확함 |
| 제출/완료 누적 | submitted 1,400까지 상승, completed 390에서 수평 — 격차가 PENDING 적체를 직접 보여줌 |
| HTTP Request Rate | `/api/user-reviews/{id}` polling이 300 req/s까지 폭증 — PENDING 사용자들의 반복 조회 |
| E2E time_to_completed p99 | 50s 수준에서 수평 수렴 — 완료가 멈춘 상태가 지속됨 |
| JVM Live Threads | 최대 125 수준 — Spring 포화 없음 |
| Hikari Pending Connections | 0 유지 — DB connection pool 여유로움 |

해석:

- submit API와 polling GET 자체는 빠르게 응답했다.
- 그러나 실제 Supabase 조회를 포함한 추천 처리와 Spring callback 저장이 1000 VU 유입 속도를 따라가지 못했다.
- 약 700 VU 이후 완료 수가 374건에서 장시간 정체됐다.
- 테스트 종료 시 1000개 iteration이 완료되지 못하고 interrupted 됐다.
- 따라서 1000 VU에서는 추천 처리/콜백 파이프라인이 적체되고, `PENDING` 상태가 대량 누적된다.

---

## SSE 전환 근거

SSE 전환 근거는 다음 문장으로 정리한다.

```text
1000 VU에서 submit/polling API 자체의 p95는 낮았지만,
전체 제출 1,374건 중 완료는 374건으로 completion coverage가 27.2%에 그쳤다.
테스트 중 PENDING polling 응답은 34,067건 누적됐고, 테스트 종료 뒤에도 PENDING 상태가 대량으로 남았다.
따라서 SSE 전환의 핵심 근거는 polling API 속도 개선이 아니라,
장시간 PENDING 상태에서 반복 조회를 줄이고 추천 진행/완료 이벤트를 push하기 위한 구조 개선이다.
```

SSE가 해결하는 것:

```text
대기 중인 사용자의 반복 polling 요청 감소
장시간 PENDING 상태에서 진행/완료 이벤트 push
프론트가 추천 처리 상태를 더 명확하게 표현할 수 있는 기반 마련
```

SSE가 해결하지 않는 것:

```text
SSE는 FastAPI 추천 처리량, Supabase 조회 성능, Spring callback timeout 자체를 해결하지 않는다.
이 병목은 별도로 callback 동시성, FastAPI worker 수, Supabase 조회 쿼리, 후보 pool 크기, timeout/retry 정책으로 다뤄야 한다.
```

---

## 발견된 문제와 원인 특정을 위한 다음 단계

### 발견된 문제

1000 VU ramping 테스트에서 추천 처리 완료율(`completion_coverage`)이 약 300 req/s 도달 시점(21:45)부터 **28% 수준에서 수평**으로 멈췄다.
제출은 1,374건까지 계속 들어왔지만 완료는 374건에서 정체됐고, 테스트 종료 후에도 PENDING 1,933건이 DB에 남았다.

Spring 레이어(Hikari Pending = 0, JVM Threads 정상)는 문제가 없었으므로, **병목은 FastAPI 추천 처리 파이프라인**에 있다.

그러나 이 테스트만으로는 파이프라인 내 어느 단계가 병목인지 특정할 수 없다. 후보는 다음과 같다:

| 병목 후보 | 근거 |
|---|---|
| FastAPI worker 수 부족 | 동시 요청이 쌓이며 처리 대기 |
| Supabase pgvector 조회 슬로우 | 1건당 조회 비용이 커서 처리량 한계 도달 |
| Spring callback timeout 누적 | `httpx.ConnectTimeout`, `CallbackError` 로그 확인됨 |
| 후보 pool 크기 | 클러스터링/재순위 연산 비용이 VU 증가에 비례해 증가 |

### 원인 특정 과정

#### 1단계 — 병목 위치 좁히기 체크리스트

1000 VU 테스트 직후, 다음 순서로 병목 위치를 좁혔다.

| 체크 항목 | 확인 방법 | 결과 |
|---|---|---|
| Spring Tomcat thread 포화 | Grafana `Tomcat Busy Threads` | 최대 4 — 정상 |
| Hikari DB connection pool 고갈 | Grafana `Hikari Pending Connections` | 0 유지 — 정상 |
| Spring 레이어 문제 | 위 두 지표 종합 | Spring은 병목 아님 |
| FastAPI callback 실패 | FastAPI 로그 `ConnectTimeout`, `CallbackError` | **다수 발생** |

Spring이 여유로운데 callback이 실패했으므로, **FastAPI → Spring 구간**에 문제가 있다고 판단했다.

#### 2단계 — 구간별 latency 측정

추천 처리 지연인지 callback 전달 실패인지 분리하기 위해 `recommendation_service.py`에 구간별 DEBUG 로그를 추가했다.

```text
embedding done       | review_id=7761 | elapsed=0.000s
pgvector search done | review_id=7761 | elapsed=1.870s   ← 최대 2.1s
rerank done          | review_id=7761 | elapsed=0.479s
reason generation done | review_id=7761 | elapsed=1.209s ← 최대 3.0s
processing done, sending callback | review_id=7761 | total_elapsed=4.769s
```

`processing done, sending callback` 로그는 찍혔지만 `callback done` 로그는 찍히지 않았다.
즉 **추천 처리는 완료됐으나 Spring callback 전달에서 실패**하고 있었다.

#### 3단계 — callback 실패 원인 가설 수립

FastAPI 로그에서 전체 스택트레이스를 확인했다.

```text
ai-api-1  | ERROR:app.services.recommendation_service:Spring callback failed:
ai-api-1  | Traceback (most recent call last):
ai-api-1  |   File ".../httpcore/_async/connection.py", line 124, in _connect
ai-api-1  |     stream = await self._network_backend.connect_tcp(**kwargs)
ai-api-1  |   File ".../httpcore/_exceptions.py", line 14, in map_exceptions
ai-api-1  |     raise to_exc(exc) from exc
ai-api-1  | httpcore.ConnectTimeout
ai-api-1  |
ai-api-1  | The above exception was the direct cause of the following exception:
ai-api-1  |
ai-api-1  |   File ".../app/clients/spring_callback_client.py", line 43, in _post_callback
ai-api-1  |     response = await self.http_client.post(url, ...)
ai-api-1  | httpx.ConnectTimeout
ai-api-1  |
ai-api-1  |   File ".../app/clients/spring_callback_client.py", line 51, in _post_callback
ai-api-1  |     raise CallbackError(str(exc)) from exc
ai-api-1  | app.core.exceptions.CallbackError
```

`connect_tcp` 단계에서 TCP 연결 자체를 못 맺고 있었다. Spring이 여유롭다는 건 Grafana에서 이미 확인됐으므로 "Spring이 바빠서"는 아니었다.

여기서 스택트레이스만으로 원인을 확정할 수는 없었다. 다만 `httpx.AsyncClient()` 기본값이 `max_connections=10`으로, 싱글 프로세스에서 동시에 수백 건 callback을 보내려 하면 pool이 꽉 차서 새 연결을 못 맺을 수 있다는 가설을 세웠다.

이를 검증하기 위해 pool을 100으로 늘려서 재측정했다.

**왜 풀 부족이 ConnectTimeout으로 나타나나**

httpx의 `AsyncClient`는 내부적으로 커넥션 풀을 가지고 있다. 풀이 가득 찬 상태에서 새 요청이 오면:

```
새 요청 들어옴
  └─ 풀에서 커넥션 꺼내려 함
       └─ 풀이 꽉 참 → 빈 슬롯 대기
            └─ 대기 시간이 connect_timeout 초과
                 └─ ConnectTimeout 발생
```

실제로 Spring이 죽어있거나 네트워크 문제가 아니라, **연결 자체를 시도도 못 하고** 풀 대기 중에 타임아웃이 난 것이다.

**왜 에러 메시지가 오해를 유도하나**

`connect_tcp`에서 터진 것처럼 보이지만, 풀 대기 타임아웃과 실제 TCP 연결 타임아웃이 같은 `ConnectTimeout`으로 올라온다. httpx가 두 케이스를 구분하지 않고 동일한 예외로 처리하기 때문에 처음엔 Spring 서버 문제처럼 보일 수 있다.

#### 4단계 — connection pool 확장 후 재측정 (500 VU)

```python
httpx.AsyncClient(limits=httpx.Limits(max_connections=100, max_keepalive_connections=20))
```

500 VU 조건으로 재측정한 결과:

| 항목 | 수정 전 (1000 VU) | 수정 후 (500 VU) |
|---|---:|---:|
| submitted | 1,374 | 1,328 |
| completed | 374 | **998** |
| completion coverage | 27.2% | **75.2%** |
| ConnectTimeout | 다수 | **0건** |
| callback done 로그 | - | **1,328건 (전량 성공)** |

callback은 전량 성공했다. 남은 330건 미완료는 callback 실패가 아니라 **k6 MAX_WAIT_SECONDS(180s) 초과**로 k6가 먼저 포기한 것이다.

FastAPI 로그를 확인하면 callback done이 1,328건으로 제출 전체와 일치한다. 즉 FastAPI는 330건도 결국 처리 완료하고 Spring에 전달했지만, k6가 이미 타임아웃으로 집계를 끊은 뒤였다. **실제 데이터 유실은 없다.**

결론: connection pool 확장으로 callback 전달 문제는 완전히 해결됐다. 남은 과제는 처리 속도(pgvector 조회 latency, reason generation 시간)이며, 이는 Supabase 원격 조회 특성상 구조적 접근이 필요한 영역이다.

#### 5단계 — 처리 속도 병목 분석

callback 문제 해결 후 `time_to_completed avg=34s`가 남아있어 구간별 로그로 원인을 분석했다.

```text
pgvector search: 0.05s ~ 1.3s
rerank:          0.09s ~ 0.27s
reason generation: 0.009s ~ 3.2s  ← 주범
```

reason generation이 mock임에도 최대 3.2s가 나왔다. mock 자체는 거의 0초여야 하는데, 같은 시점에 시작된 요청들의 elapsed가 계단식으로 줄어드는 패턴이 관찰됐다:

```text
review_id=9094 | reason generation elapsed=3.236s
review_id=9088 | reason generation elapsed=2.750s
review_id=9097 | reason generation elapsed=1.747s
review_id=9090 | reason generation elapsed=0.997s
review_id=9096 | reason generation elapsed=0.517s
review_id=9089 | reason generation elapsed=0.009s
```

이는 reason generation 자체가 느린 게 아니라, **asyncio 이벤트 루프가 다른 코루틴을 처리하느라 늦게 돌아오는 대기 시간**이 elapsed에 포함된 것이다. 싱글 프로세스에서 동시 요청이 몰리면 이벤트 루프 대기 줄이 길어져 처리 시간이 늘어나는 구조적 한계다.

#### candidate_pool_size 축소 실험 (50 → 20)

pgvector 조회 범위를 줄이면 처리 시간이 줄어들 것이라는 가설로 pool_size를 20으로 줄여 재측정했다.

| 항목 | pool_size=50 | pool_size=20 |
|---|---:|---:|
| completed | 998 | 871 |
| completion coverage | 75.2% | 72.0% |
| time_to_completed avg | 34.43s | 37.81s |

오히려 악화됐다. pgvector 조회 시간 자체는 줄었지만, 병목이 pgvector가 아닌 이벤트 루프 대기였으므로 전체 처리 시간은 개선되지 않았다. pool_size는 50으로 복원했다.

**결론**: 처리 속도 병목은 pgvector 조회량이 아니라 **싱글 프로세스 이벤트 루프 대기**다. worker 수를 늘려 이벤트 루프를 분산시키는 것이 다음 시도다.

**왜 reason generation만 유난히 긴가**

다른 단계는 이벤트 루프에 코루틴 1개만 올라가는데, reason generation은 `asyncio.gather`로 top-k 3개를 동시에 띄운다. 요청 1건당 코루틴 수가 다른 단계의 3배다.

```
embedding:        VU × 1 코루틴
pgvector search:  VU × 1 코루틴
rerank:           VU × 1 코루틴 (동기)
reason generation: VU × 3 코루틴  ← 이벤트 루프 부하 3배
```

500VU에서 reason generation 구간에만 1,500개 코루틴이 이벤트 루프 1개에 몰리므로, 대기 줄이 다른 단계보다 3배 길어진다.

**worker 수를 늘리면 코루틴이 분산되는가**

uvicorn `--workers 4`는 멀티 프로세스로, 이벤트 루프가 4개 생긴다. 500VU가 4개 루프에 분산되면 각 루프가 약 125VU(reason generation 기준 375코루틴)씩 처리하게 된다.

프로세스마다 `lifespan`에서 독립적으로 `httpx.AsyncClient`가 생성되므로 connection pool도 프로세스별로 분리된다. worker 4개 기준 실질적인 pool은 `100 × 4 = 400`개다.

#### 6단계 — worker 4개로 재측정 (500 VU)

```
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

| 항목 | worker=1 | worker=4 |
|---|---:|---:|
| submitted | 1,328 | 3,709 |
| completed | 998 | **3,709** |
| completion coverage | 75.2% | **100%** |
| time_to_completed avg | 34.43s | **11.12s** |
| time_to_completed p95 | 60s | **21.01s** |
| time_to_completed max | 1m6s | **39.03s** |
| e2e_timeout | 발생 | **0건** |
| 모든 threshold | 미통과 | **전부 통과** |

submitted와 completed가 3,709건으로 완전히 일치했다. worker=1 대비 처리 시간이 avg 기준 **3배 개선(34s → 11s)** 됐고, 미완료 건수도 0이 됐다.

이벤트 루프가 4개로 분산되면서 reason generation 구간의 코루틴 대기 줄이 해소된 것이 원인이다. 가설이 데이터로 검증됐다.

#### 7단계 — worker 4개 + 1000 VU 재측정

| 항목 | worker=1 (1000VU) | worker=4 (500VU) | worker=4 (1000VU) |
|---|---:|---:|---:|
| submitted | 1,374 | 3,709 | 4,227 |
| completed | 374 | 3,709 | **3,930** |
| completion coverage | 27.2% | 100% | **92.9%** |
| time_to_completed avg | - | 11.12s | **19.61s** |
| time_to_completed p95 | - | 21.01s | **33.02s** |
| time_to_completed max | - | 39.03s | **57.05s** |
| e2e_timeout | 다수 | 0건 | **0건** |
| 모든 threshold | 미통과 | 전부 통과 | **전부 통과** |

1000VU에서도 모든 threshold를 통과했다. 미완료 297건(4,227 - 3,930)은 k6 MAX_WAIT_SECONDS 초과로 집계에서 빠진 것이며, FastAPI 로그상 callback 실패는 아니다.

500VU 대비 VU가 2배로 늘어 처리 시간이 avg 11s → 19s로 늘었지만, worker=1 시절 27.2%였던 coverage가 92.9%까지 회복됐다.

**최종 결론**: httpx connection pool 확장 + uvicorn worker 4개 조합으로 1000VU에서도 안정적으로 동작하는 것을 확인했다. 처음 27.2%였던 completion coverage가 단계적 원인 분석과 두 가지 수정으로 92.9%까지 개선됐다.

---

## 다음 측정에서 추가로 기록할 항목

| 항목 | 기록 이유 |
|---|---|
| `completion coverage` | 전체 제출 대비 실제 완료 비율을 보여준다. |
| `interrupted iterations` | 테스트 종료 시점까지 완료되지 못한 사용자 흐름 수를 보여준다. |
| `pending_responses` | polling이 장시간 대기 상태에서 만드는 반복 조회량을 보여준다. |
| `polling_count_per_review p95` | 사용자 1명당 상태 조회가 얼마나 반복되는지 보여준다. |
| Spring DB `PENDING/COMPLETED` 수 | 테스트 종료 후 backlog가 실제 저장소에 남았는지 확인한다. |
| FastAPI callback timeout 로그 | 추천 처리 완료 후 Spring callback 저장 경로의 병목 여부를 확인한다. |
| Grafana Tomcat/Hikari 지표 | Spring request thread와 DB connection pool 압력을 확인한다. |
