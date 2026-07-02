# [Frontend] 특정 앨범 상세 페이지 빈 화면

**날짜**: 2026-07-02
**영역**: Frontend — `CriticsReviewDetail.tsx`

---

## 증상

일부 앨범 상세 페이지(`/critics/{id}`)가 빈 화면으로 표시됨. 다른 앨범은 정상.

## 원인

GPT가 `reviewSummary`의 `track_info.korean` 구조를 앨범마다 다르게 생성함.

- 정상 앨범: `korean: { "트랙명": "설명" }`
- 문제 앨범: `korean: { track_name: { "트랙명": "설명" } }` ← 한 겹 더 중첩

`parseSummary`가 `track_name` 중첩을 모르고 `{ track_name: { ... } }` 그대로 사용.
렌더링 시 `<p>{data}</p>`에서 `data`가 객체가 되어 React가 `Objects are not valid as a React child` 에러를 던짐.
이 에러는 컴포넌트 트리 전체를 unmount시키므로 페이지 전체가 빈 화면이 됨.

## 수정 (`CriticsReviewDetail.tsx`)

`track_name` 키가 있으면 그 안쪽을 꺼내도록 방어 처리.

```ts
const trackRaw = p.categories?.track_info?.korean ?? {};
const trackInfoKorean =
  typeof trackRaw.track_name === "object" && trackRaw.track_name !== null
    ? trackRaw.track_name
    : trackRaw;
```

## 규모 확인 (2026-07-02)

- 전체 `processed_summaries`: 23,966건
- `track_name` 중첩 구조: 2,690건 (약 11%)
- GPT가 일관되지 않게 구조를 다르게 뱉은 것이 확인됨

## 후속 조치

- [ ] **파이프라인 프롬프트 수정** — GPT 프롬프트에 `track_info.korean`의 구조를 명시(`{ "트랙명": "설명" }` 형태만 허용). 현재 프롬프트가 구조를 강제하지 않아 11%가 다른 형태로 저장됨.
- [ ] **기존 데이터 정규화** — 아래 SQL로 2,690건을 찾아 `track_name` 한 겹을 벗겨서 업데이트하거나, 파이프라인 재실행으로 덮어씀.
  ```sql
  SELECT COUNT(*)
  FROM processed_summaries
  WHERE summary_data::jsonb -> 'categories' -> 'track_info' -> 'korean' ? 'track_name';
  ```
- [ ] **`parseSummary` 단위 테스트 추가** — `track_name` 중첩 구조 / 정상 구조 두 케이스를 모두 커버하는 테스트 작성.
