# ADR-FE003: 프론트엔드 테스트 전략

## Context

프론트엔드는 폼 입력, API 응답 분기, polling timer, retry, 라우팅을 검증해야 한다.
모든 케이스를 Playwright E2E로만 검증하면 테스트가 느리고, 실패 원인을 좁히기 어렵다.
반대로 컴포넌트 테스트만으로는 실제 사용자 플로우와 라우팅을 충분히 검증하기 어렵다.

---

## Decision

테스트는 빠른 단위부터 느린 E2E 순서로 작성한다.

| Phase | 도구 | 검증 대상 | 외부 의존성 |
|-------|------|-----------|-------------|
| Phase 1 | Vitest | config, 순수 함수, API response parser | 없음 |
| Phase 2 | React Testing Library + Vitest | 단일 Component 렌더링, 폼 입력, 버튼 상태, 상태별 UI, custom hook | 없음 또는 props/callback stub |
| Phase 3 | React Testing Library + Vitest + MSW + fake timer | Page 상태 분기, 여러 컴포넌트 조합, polling timer, retry, 에러 처리 | API/timer mock |
| Phase 4 | Playwright | 실제 사용자 플로우, 라우팅, 핵심 API 연동 흐름 | 테스트 서버 또는 MSW handler 재사용 |

---

## Phase 경계

- Phase 1은 React 렌더링 없이 실행 가능한 순수 로직을 검증한다.
- Phase 2는 단일 Component 또는 custom hook을 검증한다. API 호출, router, timer 같은 외부 의존성은 직접 다루지 않는다.
- Phase 3은 Page 단위 조합을 검증한다. 여러 Component가 함께 동작하며, API 응답과 timer는 mock한다.
- Phase 4는 브라우저에서 사용자 관점의 핵심 경로를 검증한다. 세부 상태 조합은 Phase 2/3에서 검증한다.

---

## API Mock 전략

Page 테스트의 API mock은 MSW(Mock Service Worker)를 기본으로 사용한다.

| 옵션 | 특징 | 결정 |
|------|------|------|
| `vi.mock('fetch')` 또는 axios mock | 빠르고 단순하지만 네트워크 계층을 우회한다. 테스트별 mock이 흩어지기 쉽다. | 기각 |
| MSW | 실제 네트워크 요청 계층에서 가로채며, RTL/Vitest와 Playwright에서 handler를 재사용할 수 있다. | 채택 |

MSW handler는 [API_SPEC.md](../../API_SPEC.md) 응답 형태와 동일하게 작성한다.
API mock 응답은 handler 파일에서 중앙 관리하고, 테스트별 임의 응답 shape를 만들지 않는다.

---

## 커버리지 기준

초기 기준은 Phase 1~3에 적용한다.
Playwright E2E는 라인 커버리지 목표에 포함하지 않고, 핵심 사용자 경로 통과 여부를 본다.

| 대상 | 기준 |
|------|------|
| Phase 1~3 | line coverage 80% 이상 |
| Phase 4 | 핵심 사용자 플로우 통과 |

커버리지 기준은 프론트 코드 규모와 테스트 안정성이 확인된 뒤 조정할 수 있다.

---

## 원칙

1. 테스트 범위 분리
   - 상태 조합은 React Testing Library + Vitest에서 검증한다.
   - Playwright는 핵심 사용자 경로만 검증한다.
   - E2E는 사용자 관점의 성공/실패 핵심 경로를 검증하고, 세부 상태 조합을 중복 검증하지 않는다.

2. 시간 기반 로직
   - polling interval 계산은 Vitest 단위 테스트로 검증한다.
   - polling timer와 cleanup은 fake timer로 검증한다.

3. Custom hook
   - custom hook은 `renderHook`으로 검증하고 Phase 2에 둔다.
   - API/timer와 결합된 hook은 Phase 3 기준을 따른다.

4. API mock
   - API mock 응답은 MSW handler로 관리한다.
   - MSW handler는 [API_SPEC.md](../../API_SPEC.md)와 동일한 응답 형태를 사용한다.

---

## 구현 순서

1. Config/순수 함수 테스트를 먼저 작성한다.
2. Component/custom hook 테스트로 렌더링, 사용자 입력, hook 상태를 검증한다.
3. Page 테스트로 MSW API 응답별 상태 분기와 timer 동작을 검증한다.
4. Playwright E2E로 실제 라우팅과 사용자 플로우를 검증한다.

---

## Consequences

- 실패 원인을 Unit, Component/Page, E2E 단계별로 좁힐 수 있다.
- polling과 retry 같은 시간 기반 로직을 빠른 테스트에서 안정적으로 검증할 수 있다.
- MSW handler로 API mock 응답을 중앙 관리해 API 계약 drift를 줄인다.
- E2E 테스트 수를 핵심 플로우 중심으로 유지해 실행 시간을 줄인다.
