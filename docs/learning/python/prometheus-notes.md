# Prometheus 메트릭 학습 노트

최종 업데이트: 2026-07-10

---

## Prometheus란?

시계열 모니터링 시스템이다. 애플리케이션이 `/metrics` 엔드포인트에 측정값을 노출하면, Prometheus 서버가 주기적으로 긁어가서(scrape) 저장한다.

```
[FastAPI 앱] --/metrics--> [Prometheus 서버] --> [Grafana 대시보드]
```

이 프로젝트에서는 Prometheus가 5초마다 `ai-api:8000/metrics`를 scrape한다.

파일: `load-tests/observability/prometheus.yml`

---

## Python에서 사용: `prometheus_client` 라이브러리

`prometheus_client` 패키지가 메트릭 객체를 제공한다. 메트릭을 선언하면 자동으로 `/metrics` 응답에 포함된다.

---

## 3가지 메트릭 타입

### 1. Counter — 누적 횟수

값이 오직 증가만 하는 메트릭이다. 요청 수, 에러 수 등에 사용한다.

```python
from prometheus_client import Counter

recommendation_requests_total = Counter(
    "jazzmate_recommendation_requests_total",    # 메트릭 이름
    "FastAPI recommendation requests by status.",  # 설명
    ("status",),                                   # 라벨 (분류 기준)
)

# 사용
recommendation_requests_total.labels(status="completed").inc()
recommendation_requests_total.labels(status="failed_embedding").inc()
```

Prometheus에서 조회하면 이렇게 보인다:

```
jazzmate_recommendation_requests_total{status="completed"} 42
jazzmate_recommendation_requests_total{status="failed_embedding"} 3
```

> Counter는 절대 감소하지 않는다. "현재 초당 요청 수"를 보려면 Prometheus 쿼리에서 `rate()` 함수를 쓴다:
> `rate(jazzmate_recommendation_requests_total[5m])`

### 2. Histogram — 시간 분포 측정

값의 분포를 측정한다. API 응답 시간처럼 "얼마나 걸렸는지"를 추적할 때 사용한다.

```python
from prometheus_client import Histogram

recommendation_stage_latency = Histogram(
    "jazzmate_recommendation_stage_duration_seconds",
    "FastAPI recommendation processing stage latency.",
    ("stage", "status"),              # 라벨: 어떤 단계인지, 성공/실패인지
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
)

# 사용
recommendation_stage_latency.labels(stage="embedding", status="success").observe(0.35)
```

Histogram은 내부적으로 버킷(bucket)별 카운터를 만든다:

```
# 0.5초 이하로 걸린 요청이 몇 개인지
jazzmate_recommendation_stage_duration_seconds_bucket{stage="embedding",le="0.5"} 120
jazzmate_recommendation_stage_duration_seconds_bucket{stage="embedding",le="1.0"} 125
# 전체 요청 수
jazzmate_recommendation_stage_duration_seconds_count{stage="embedding"} 130
# 전체 소요시간 합계
jazzmate_recommendation_stage_duration_seconds_sum{stage="embedding"} 45.2
```

> p99 응답시간 등을 계산할 때는 `histogram_quantile()` 함수를 쓴다:
> `histogram_quantile(0.99, rate(jazzmate_recommendation_stage_duration_seconds_bucket[5m]))`

### 3. Gauge — 현재 값

올라갈 수도, 내려갈 수도 있는 값이다. 현재 처리 중인 요청 수, 메모리 사용량 등에 사용한다.

```python
from prometheus_client import Gauge

recommendation_in_flight = Gauge(
    "jazzmate_recommendation_in_flight",
    "Recommendation requests currently in flight.",
    multiprocess_mode="livesum",  # 멀티프로세스 환경용 설정
)

# 요청 시작 시
recommendation_in_flight.inc()
# 요청 끝나면
recommendation_in_flight.dec()
```

> `multiprocess_mode="livesum"`은 gunicorn처럼 여러 워커 프로세스가 뜰 때, 각 프로세스의 값을 합산하라는 의미다.

---

## 라벨(Label) — 메트릭을 세분화하는 태그

같은 메트릭을 라벨로 나눠서 기록할 수 있다.

```python
# 라벨 정의
Counter("requests_total", "...", ("method", "endpoint"))

# 라벨 값 지정
requests_total.labels(method="GET", endpoint="/albums").inc()
requests_total.labels(method="POST", endpoint="/reviews").inc()
```

라벨 조합마다 별도 시계열이 생긴다. 라벨 종류가 너무 많으면(user_id 같은) 시계열 폭발(cardinality explosion)이 일어나므로 주의한다.

---

## 이 프로젝트의 메트릭 설계

파일: `backendPython/app/observability/metrics.py`

| 메트릭 | 타입 | 용도 |
|---|---|---|
| `jazzmate_recommendation_stage_duration_seconds` | Histogram | 추천 파이프라인의 각 단계(embedding, pgvector_search, rerank 등) 소요 시간 |
| `jazzmate_recommendation_requests_total` | Counter | 추천 요청의 최종 상태별(completed, failed_embedding 등) 누적 횟수 |
| `jazzmate_recommendation_in_flight` | Gauge | 현재 처리 중인 추천 요청 수 |

---

## `observe_recommendation_stage` — contextmanager 패턴

`with` 문으로 코드 블록의 시간을 자동 측정하는 패턴이다.

```python
from contextlib import contextmanager

@contextmanager
def observe_recommendation_stage(stage: str):
    started_at = time.monotonic()
    status = "success"
    try:
        yield                    # 여기서 with 블록 안의 코드가 실행된다
    except Exception:
        status = "error"         # 예외 발생 시 status를 바꾼다
        raise                    # 예외는 다시 던진다
    finally:
        recommendation_stage_latency.labels(stage=stage, status=status).observe(
            time.monotonic() - started_at
        )
```

사용하는 쪽 코드:

```python
with observe_recommendation_stage("embedding"):
    embedding = await self.embedding_service.embed_review(review_content)
```

이렇게 하면:
- 성공 시: `stage="embedding", status="success"` 라벨로 소요시간 기록
- 예외 시: `stage="embedding", status="error"` 라벨로 소요시간 기록 후 예외를 다시 던짐

---

## `_NoopMetric` — prometheus_client 없을 때 대체 객체

로컬 개발 환경에서 `prometheus_client`가 설치 안 돼 있어도 에러 없이 동작하도록, 아무것도 안 하는 가짜 메트릭 객체를 제공한다.

```python
class _NoopMetric:
    def labels(self, **kwargs):
        return self              # 자기 자신을 반환해서 체이닝이 가능
    def inc(self, amount=1.0):
        pass                     # 아무것도 안 함
    def observe(self, amount):
        pass
```

`if Histogram is not None:`로 분기해서 실제 메트릭 또는 Noop을 할당한다. 사용하는 쪽 코드는 둘 다 같은 인터페이스이므로 분기 없이 동작한다.

---

## Prometheus scrape 설정

파일: `load-tests/observability/prometheus.yml`

```yaml
scrape_configs:
  - job_name: "ai-api"
    metrics_path: "/metrics"         # FastAPI 앱의 메트릭 엔드포인트
    static_configs:
      - targets: ["ai-api:8000"]     # Docker 네트워크 내 서비스명:포트
```

`scrape_interval: 5s`이므로 5초마다 `/metrics`를 호출해서 값을 가져간다.

---

## 요약: 메트릭 데이터 흐름

```
1. FastAPI 앱 시작 → prometheus_client가 메트릭 객체 등록
2. 추천 요청 들어옴 → inc_recommendation_in_flight() (Gauge +1)
3. 각 단계 실행 → observe_recommendation_stage()가 Histogram에 소요시간 기록
4. 요청 완료/실패 → Counter에 상태별 횟수 +1, Gauge -1
5. Prometheus가 5초마다 /metrics를 scrape → 시계열 DB에 저장
6. Grafana가 Prometheus에서 데이터를 쿼리해서 대시보드에 시각화
```
