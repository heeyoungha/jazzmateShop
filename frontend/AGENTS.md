# 프론트엔드 규칙

> 적용 범위: `frontend/` 디렉터리의 React 애플리케이션
> 공통 규칙: [루트 AGENTS.md](../AGENTS.md)

---

## 설계 문서

구현 전 아래 문서를 먼저 확인한다.

| 문서 | 내용 | 언제 확인할지 |
|------|------|---------------|
| [docs/frontend/SDD.md](../docs/frontend/SDD.md) | 프론트엔드 책임 경계, 플로우 문서 인덱스 | 기능 구현 전, 구조 변경 시 |
| [docs/frontend/flows/](../docs/frontend/flows/) | 페이지별 요구사항, 컴포넌트, 분기 로직 | 페이지/플로우 구현 전 |
| [docs/API_SPEC.md](../docs/API_SPEC.md) | API 요청/응답 계약 | API client, 타입, 에러 처리 구현 시 |
| [docs/SDD.md](../docs/SDD.md) | 공통 라우팅, 프론트 의존 필드, 추천 상태 전이 | polling, retry, 라우팅 변경 시 |

---

## 설계 기준 (ADR)

구현 변경 시 아래 ADR을 우선 확인한다.

| ADR | 주제 | 언제 확인할지 |
|---|---|---|
| [ADR-FE001](../docs/frontend/adr/001-state-and-api-response.md) | 상태 소유와 API 응답 처리 | API client, Page 상태, 응답 파싱 변경 시 |
| [ADR-FE002](../docs/frontend/adr/002-recommendation-polling-ui.md) | 추천 상태 polling UI | polling, retry, 추천 결과 UI 변경 시 |
| [ADR-FE003](../docs/frontend/adr/003-frontend-test-strategy.md) | 프론트엔드 테스트 전략 | 테스트 도구 선택, 테스트 범위, E2E 범위 변경 시 |

---

## 기술 스택

| 역할 | 기술 |
|------|------|
| UI | React 18 + TypeScript |
| 빌드 | Vite |
| 라우팅 | React Router |
| 스타일 | Tailwind CSS + shadcn/ui |
| E2E | Playwright |

---

## 코딩 컨벤션

### 구조

| 대상 | 규칙 |
|------|------|
| 페이지 | `src/pages/{PageName}.tsx` |
| 공통 컴포넌트 | `src/components/` |
| API client | `src/api/` |
| 설정/정책값 | `src/config/` |
| 타입 | `src/types/` 또는 API client 근처에 colocate |
| hooks | `src/hooks/` |
| 유틸 | `src/lib/` |

라우트 단위 데이터 요청과 상태 분기는 Page가 담당한다.
Component는 props를 받아 렌더링하고, 직접 API를 호출하지 않는다.
추천 polling interval 같은 UX/운영 정책값은 `src/config/polling.ts`에서 관리한다.

### 네이밍

| 대상 | 규칙 |
|------|------|
| 컴포넌트 | `PascalCase` |
| 파일 | 컴포넌트/Page는 `PascalCase.tsx`, 유틸/API/hook은 `camelCase.ts` |
| hook | `useXxx` |
| 타입/interface | `PascalCase` |
| 상수 | `UPPER_SNAKE_CASE` |

### TypeScript

- API 응답 타입을 명시한다.
- `any`는 금지한다. 외부 응답이 불명확하면 `unknown`으로 받은 뒤 좁힌다.
- nullable 필드는 API 명세와 동일하게 표현한다.
- enum성 문자열은 union type으로 고정한다.

```ts
type RecommendationStatus = 'PENDING' | 'COMPLETED' | 'FAILED';
```

### API 처리

API 응답 형태는 [API_SPEC.md](../docs/API_SPEC.md#1-공통-규칙)를 따른다.

| API 유형 | 처리 |
|----------|------|
| POST 성공 | `ApiResponse<T>`로 파싱한다. `success`, `message`, `data`를 확인한다. |
| GET 단건 | DTO를 직접 사용한다. |
| GET 목록 | 배열 또는 Page 응답을 직접 사용한다. |
| 에러 | `ErrorResponse.message`를 화면 에러 메시지로 사용한다. |

- 프론트가 의존하는 API 필드와 타입은 API_SPEC.md에 명시된 계약을 따른다.
- 문서에 없는 백엔드 내부 필드에 기대어 화면을 분기하지 않는다.
- 테스트 fixture, MSW handler, Component props, Page state는 API 계약과 같은 필드명과 타입을 사용한다.
- 테스트 편의를 위해 id, 날짜, 숫자, nullable/optional 여부 같은 응답 타입을 임의로 바꾸지 않는다.
- POST 이후 응답 `data`로 라우팅하거나 후속 요청을 시작하는 Page는 `res.ok`뿐 아니라 `success === true`와 실제로 사용하는 필드 존재 여부를 확인한다.
- Page는 자신이 의존하는 API 상태와 실패 경로를 화면 상태로 변환한다. 네트워크 오류, JSON 파싱 오류, 사용하는 필드 누락은 일반 장애 메시지로 처리한다.

### React State

- 서버 요청 결과처럼 `loading`, `success`, `notFound`, `error`가 서로 배타적인 Page 상태는 여러 boolean과 nullable data 조합 대신 discriminated union 하나로 관리한다.
- route param 또는 요청 key가 바뀌면 이전 success/error/notFound 상태를 `loading`으로 reset한다.
- `useEffect`에서 비동기 요청을 실행할 때는 cleanup flag 또는 AbortController로 stale response가 최신 상태를 덮지 않게 한다.
- API 요청 중 상태(`loading`, `loadingRef`, submit/retry loading)는 성공, HTTP error, 네트워크 오류, JSON 파싱 오류 모든 경로에서 복구되도록 `finally` 또는 동등한 cleanup을 둔다.
- route param 기반 GET 요청은 param이 없거나 유효하지 않으면 요청하지 않고 not found 또는 error 상태로 분기한다.

### Form

- 필수 필드는 클라이언트에서 1차 검증한다.
- 서버 400 응답의 `message`는 폼 에러로 표시한다.
- 제출 중에는 submit 버튼을 비활성화해 중복 요청을 막는다.
- 서버 검증을 우회할 수 없으므로 클라이언트 검증만으로 성공을 가정하지 않는다.
- 단순 폼은 입력값마다 `useState`를 만들지 않고, 제출 시 `FormData`로 값을 수집하는 uncontrolled form을 우선한다.
- 입력 중 실시간 미리보기, 조건부 UI, 즉시 검증처럼 렌더링 상태가 필요한 경우에만 controlled input을 사용한다.
- 필수 문자열 검증은 백엔드 `@NotBlank`와 맞춰 `trim()` 기준으로 처리한다.
- 선택 숫자 필드는 `type="number"`를 사용하고, 제출 시 `Number.isFinite`로 유효한 숫자만 payload에 포함한다.

### Polling

- `ReviewBasedRecommendPage`에서만 추천 상태 polling을 관리한다.
- 페이지 진입 시 즉시 `GET /api/user-reviews/{id}`를 호출한다.
- `PENDING`이면 timer를 유지한다.
- `COMPLETED` 또는 `FAILED`이면 timer를 중단한다.
- 페이지 이탈 시 timer를 반드시 cleanup한다.
- `FAILED` 상태 조회만으로 retry를 자동 호출하지 않는다.
- retry는 사용자가 `POST /api/user-reviews/{id}/retry`를 명시적으로 실행할 때만 호출한다.

### Error UI

- 400: `ErrorResponse.message`를 사용자 수정 가능한 에러로 표시한다.
- 404: 찾을 수 없음 상태를 표시하고, 필요하면 목록/이전 화면 이동을 제공한다.
- 500: 일반 장애 메시지를 표시한다. 내부 stack trace나 서버 상세 정보는 노출하지 않는다.
- `!res.ok` 전체를 하나의 에러 상태로 뭉개지 않는다. 최소한 404와 그 외 오류를 분리한다.
- 네트워크 오류와 JSON 파싱 오류는 찾을 수 없음으로 처리하지 않고 일반 장애 메시지로 표시한다.

### UI

- 첫 화면은 실제 사용 가능한 화면이어야 한다. 마케팅용 랜딩 페이지를 만들지 않는다.
- 작업형 화면은 조용하고 스캔 가능한 레이아웃을 우선한다.
- 버튼, 입력, 카드, 빈 상태, 로딩, 에러 상태를 모두 구현한다.
- 텍스트가 모바일/데스크톱에서 부모 요소를 넘치지 않도록 한다.
- 아이콘이 필요한 버튼은 lucide 아이콘을 우선 사용한다.

---

## 테스트 기준

테스트 전략은 [ADR-FE003](../docs/frontend/adr/003-frontend-test-strategy.md)을 따른다.

| 테스트 | 검증 대상 |
|--------|-----------|
| Unit/Component/Page | 폼 검증, 상태별 렌더링, retry 버튼 노출, API/timer mock |
| E2E Playwright | 작성 → 저장 → 추천 페이지 이동, polling → 결과 렌더링, FAILED → retry |

E2E는 사용자 관점 플로우를 검증한다.
Page 테스트의 API mock은 MSW handler를 기본으로 사용한다.
API mock을 쓸 경우 실제 [API_SPEC.md](../docs/API_SPEC.md) 응답 형태와 동일해야 한다.
Form 테스트는 빈 값뿐 아니라 공백 문자열 입력도 검증한다.
Page 테스트는 해당 Page가 의존하는 HTTP 오류, 네트워크 실패, 사용하는 필드 누락 같은 방어 로직을 검증한다.
route param 기반 조회 Page 테스트는 API 명세의 실제 id 타입을 fixture에 사용한다.
Phase 1~3 테스트는 line coverage 80% 이상을 초기 기준으로 한다.
