# ADR-BJ003: AI 추천 상태 확인 방식

## Context

JazzmateShop은 감상문 저장 후 FastAPI에 AI 추천을 비동기로 요청한다. FastAPI가 추천 결과를 Spring Boot로 콜백하면, 프론트엔드는 추천 상세 페이지에서 상태를 확인하고 결과를 표시해야 한다.

현재 요구사항의 특징은 다음과 같다.

- 프론트엔드는 `recommendationStatus`에 따라 `PENDING`, `COMPLETED`, `FAILED`를 분기한다.
- `PENDING`이면 일정 간격으로 상태를 다시 조회한다.
- `COMPLETED`이면 `recommendations[]`를 렌더링한다.
- `FAILED`이면 retry 버튼을 노출하고, 사용자가 명시적으로 `POST /api/user-reviews/{id}/retry`를 호출한다.
- 추천 진행률이나 단계별 실시간 이벤트는 현재 요구사항이 아니다.
- 초기 배포는 단일 또는 소규모 Spring Boot 인스턴스를 전제로 하지만, 수평 확장 가능성을 열어둔다.

---

## Options

### Option 1: Polling

프론트엔드가 일정 간격으로 `GET /api/user-reviews/{id}`를 호출하고, `recommendationStatus`가 `COMPLETED` 또는 `FAILED`가 될 때까지 반복한다.

| 항목 | 평가 |
|------|------|
| 구현 난이도 | 낮음 |
| 운영 복잡도 | 낮음 |
| 연결 관리 | 없음 |
| 서버 부하 | 대기 중 반복 조회 발생 |
| UX | polling interval만큼 완료 반영 지연 가능 |
| scale-out | 가장 단순. 일반 HTTP 조회라 stateless 처리 가능 |

**장점**

- 현재 상태 분기 요구사항을 그대로 만족한다.
- 서버가 클라이언트 연결 상태를 관리하지 않는다.
- 로드밸런서 뒤에 여러 Spring Boot 인스턴스를 두어도 특별한 session routing이 필요 없다.
- 장애 복구가 단순하다. 다음 polling 요청이 현재 DB 상태를 다시 읽으면 된다.
- 테스트와 디버깅이 쉽다.

**단점**

- `PENDING` 대기 중 같은 상세 조회 API를 반복 호출한다.
- polling interval을 짧게 하면 DB/API 부하가 증가하고, 길게 하면 완료 반영이 늦어진다.
- 동시 대기 사용자가 많아지면 상태 조회 트래픽이 누적될 수 있다.

**완화 전략**

- `COMPLETED` 또는 `FAILED` 수신 시 polling을 즉시 중단한다.
- 단계적으로 interval을 늘린다. 예: 최초 10초는 1초, 이후 60초까지 3초, 그 이후 5~10초.
- 최대 대기 시간을 둔다.
- k6로 동시 `PENDING` 사용자 수, 상세 조회 RPS, DB select 부하, p95/p99 응답 시간을 측정한다.

---

### Option 2: SSE (Spring MVC `SseEmitter`)

프론트엔드가 SSE 연결을 열고, Spring Boot가 추천 저장 완료 후 이벤트를 push한다.

| 항목 | 평가 |
|------|------|
| 구현 난이도 | 중간 |
| 운영 복잡도 | 중간 |
| 연결 관리 | 서버가 emitter registry 관리 |
| 서버 부하 | 반복 조회는 줄지만 장기 연결 유지 필요 |
| UX | 완료 즉시 반영 가능 |
| scale-out | 다중 인스턴스에서는 fan-out 필요 |

**장점**

- 반복 조회 없이 서버가 완료 시점을 알려줄 수 있다.
- 완료 반영 지연이 polling interval에 묶이지 않는다.
- 향후 진행 단계, 실패 사유, 여러 서버발 이벤트가 늘어나면 polling보다 자연스럽다.

**단점**

- 서버가 열린 연결과 emitter lifecycle을 관리해야 한다.
- 인메모리 registry는 단일 인스턴스에 적합하며, 다중 인스턴스에서는 이벤트 유실 가능성이 있다.
- 프록시/nginx timeout, buffering, heartbeat, reconnect 정책을 추가로 관리해야 한다.
- 현재 요구사항은 단순 상태 분기이므로 복잡도 대비 이점이 제한적이다.

---

## Decision

현재 구조에서는 **Polling을 채택한다**.

이유는 다음과 같다.

- 현재 요구사항은 지속 실시간 스트림이 아니라 `PENDING / COMPLETED / FAILED` 상태 확인과 분기 처리다.
- `GET /api/user-reviews/{id}` 하나로 대기, 완료, 실패, retry UI 분기를 모두 처리할 수 있다.
- polling은 stateless HTTP 조회이므로 수평 확장과 장애 복구가 단순하다.
- SSE는 반복 조회를 줄일 수 있지만, 서버 연결 상태와 emitter registry를 관리해야 한다.
- 다중 인스턴스 환경에서는 SSE 이벤트 fan-out을 위해 Redis Pub/Sub 같은 추가 인프라가 필요하다.

---

## Polling Policy

프론트엔드는 추천 상세 페이지에서 다음 정책으로 polling한다.

1. 페이지 진입 시 `GET /api/user-reviews/{id}`를 호출한다.
2. `recommendationStatus == PENDING`이면 대기 UI를 표시하고 일정 시간 뒤 다시 조회한다.
3. `recommendationStatus == COMPLETED`이면 `recommendations[]`를 렌더링하고 polling을 중단한다.
4. `recommendationStatus == FAILED`이면 에러 메시지와 retry 버튼을 표시하고 polling을 중단한다.
5. retry 버튼 클릭 시 `POST /api/user-reviews/{id}/retry`를 호출한다.
6. retry 성공 후 다시 `PENDING` 대기 상태로 돌아가 polling을 재개한다.

권장 interval은 다음과 같다.

| 구간 | interval |
|------|----------|
| 최초 10초 | 1초 |
| 10~60초 | 3초 |
| 60초 이후 | 5~10초 |

최대 대기 시간은 프론트 UX 정책에서 별도로 정한다.

---

## Revisit Criteria

다음 조건 중 하나가 실제 지표로 확인되면 SSE 또는 브로커 기반 push 구조를 재검토한다.

- 동시 `PENDING` 사용자가 증가해 상세 조회 API가 병목이 된다.
- polling 트래픽이 전체 API 트래픽에서 의미 있는 비중을 차지한다.
- DB select 부하 또는 p95/p99 응답 시간이 polling 때문에 악화된다.
- 완료 반영 지연을 1초 이하로 엄격히 보장해야 한다.
- 추천 진행 단계, 실패 사유, 실시간 로그 등 서버발 이벤트가 여러 개로 늘어난다.
- 여러 서비스에서 공통 실시간 알림 기능을 요구한다.

확장 순서는 다음을 우선한다.

```
단순 상태 확인             → Polling
Polling 부하/지연 문제      → SSE 검토
SSE + 다중 인스턴스         → SSE + Redis Pub/Sub fan-out
수천 장기 연결/지속 이벤트  → WebFlux 기반 realtime gateway + broker 검토
양방향 실시간 기능          → WebSocket 검토
```
