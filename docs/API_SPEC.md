# JazzmateShop — API 명세

> 호출 주체: 프론트엔드(React) / FastAPI AI 서버 (인바운드 콜백 + 아웃바운드 추천 요청)
> DTO·Entity 필드 상세: [DTO_SPEC.md](./DTO_SPEC.md)
> 플로우별 맥락: [SDD.md](./SDD.md)

---

## 목차

1. [공통 규칙](#1-공통-규칙)
2. [UserReview API](#2-userreview-api)
   - POST /api/user-reviews
   - GET /api/user-reviews
   - GET /api/user-reviews/{id}
   - POST /api/user-reviews/{id}/retry
3. [Recommendation API](#3-recommendation-api)
   - POST /recommend/by-review  ← Spring → FastAPI (아웃바운드)
   - POST /api/user-reviews/{reviewId}/recommendations  ← FastAPI → Spring (인바운드)
4. [CriticsReview API](#4-criticsreview-api)
   - GET /api/critics
   - GET /api/critics/{id}

---

## 1. 공통 규칙

### 응답 형식

```
POST 성공  →  ApiResponse<T>       { success: true,  message: "...", data: T|null }
조회 단건   →  DTO 직접 반환
조회 목록   →  List<DTO> 또는 Page<DTO> 직접 반환
FastAPI 콜백 응답  →  ResponseEntity<Void>  (body 없음)
에러       →  ErrorResponse         { success: false, message: "..." }
```

### 공통 응답 메시지

> 코드 상수: `ApiMessages`

| 상황 | message |
|------|---------|
| 감상문 생성 성공 | 감상문이 저장되었습니다. |
| 추천 재시도 시작 | 추천 재시도를 시작했습니다. |
| 서버 오류 | 서버 오류가 발생했습니다. |

### 에러 코드

| HTTP | 발생 조건 | 응답 |
|------|-----------|------|
| 400 | `@Valid` 검증 실패 (`@NotBlank` 등) | `ErrorResponse` |
| 404 | 존재하지 않는 리소스 (`ResourceNotFoundException`) | `ErrorResponse` |
| 500 | 예상 외 서버 오류 | `ErrorResponse` |

---

## 2. UserReview API


### POST /api/user-reviews

> 호출 주체: WriteReviewPage
> 감상문을 저장하고, 트랜잭션 커밋 후 AI 추천 요청을 비동기로 시작한다.

**Request**

```
Content-Type: application/json
```

```json
{
  "trackName": "So What",
  "artistName": "Miles Davis",
  "reviewContent": "처음 들었을 때의 그 고요함이 아직도 기억난다.",
  "rating": 4.5,
  "mood": "calm",
  "genre": "modal jazz",
  "energyLevel": 0.3,
  "bpm": 120,
  "vocalStyle": "instrumental",
  "instrumentation": "quintet",
  "isPublic": true
}
```

| 필드 | 필수 | 설명 |
|------|------|------|
| trackName | Y | `@NotBlank` |
| artistName | Y | `@NotBlank` |
| reviewContent | Y | `@NotBlank` |
| rating ~ isPublic | N | 선택 필드 |

**Response `201`**

```json
{
  "success": true,
  "message": "감상문이 저장되었습니다.",
  "data": {
    "id": 42
  }
}
```

> 프론트 의존 필드: `data.id` — `navigate(/recommend/${data.id})`에 사용

**Response `400`** — trackName 누락 등

```json
{ "success": false, "message": "trackName은 필수입니다." }
```

---

### GET /api/user-reviews

> 호출 주체: MyReviewsPage
> 내 감상문 목록을 페이지네이션으로 반환한다. (요약 응답)

**Request**

```
GET /api/user-reviews?page=0&size=10
```

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| page | 0 | 페이지 번호 (0-based) |
| size | 10 | 페이지 크기 |

**Response `200`**

```json
{
  "content": [
    {
      "id": 42,
      "trackName": "So What",
      "artistName": "Miles Davis",
      "reviewContent": "처음 들었을 때의 그 고요함이 아직도 기억난다.",
      "rating": 4.5,
      "mood": "calm",
      "genre": "modal jazz",
      "createdAt": "2026-05-23T10:00:00"
    }
  ],
  "totalElements": 15,
  "totalPages": 2,
  "number": 0,
  "size": 10,
  "last": false
}
```

> 프론트 의존 필드
> - `content[]`: 감상문 카드 렌더링 대상
> - `last`: `true`이면 무한 스크롤 종료
> - `number`: 다음 요청 시 `page=number+1`

---

### GET /api/user-reviews/{id}

> 호출 주체: ReviewBasedRecommendPage
> 감상문 단건 + 추천 결과를 반환한다. `recommendationStatus`에 따라 `recommendations` 포함 여부가 달라진다.

**Request**

```
GET /api/user-reviews/42
```

**Response `200`**

```json
{
  "review": {
    "id": 42,
    "userId": "user-123",
    "trackName": "So What",
    "artistName": "Miles Davis",
    "reviewContent": "처음 들었을 때의 그 고요함이 아직도 기억난다.",
    "rating": 4.5,
    "mood": "calm",
    "genre": "modal jazz",
    "energyLevel": 0.3,
    "bpm": 120,
    "vocalStyle": "instrumental",
    "instrumentation": "quintet",
    "isPublic": true,
    "isFeatured": false,
    "likeCount": 0,
    "commentCount": 0,
    "createdAt": "2026-05-23T10:00:00",
    "updatedAt": "2026-05-23T10:01:00"
  },
  "recommendationStatus": "COMPLETED",
  "hasRecommendations": true,
  "recommendations": [
    {
      "id": 1,
      "userReviewId": 42,
      "albumId": "00000000-0000-0000-0000-000000000101",
      "recommendationScore": 0.9423,
      "recommendationReason": "모달 재즈 특유의 정적인 분위기가 유사합니다.",
      "createdAt": "2026-05-23T10:01:00",
      "updatedAt": "2026-05-23T10:01:00"
    }
  ]
}
```

> 프론트 의존 필드
> - `recommendationStatus`: `PENDING` / `COMPLETED` / `FAILED` — 프론트 상태 표시용
> - `recommendations[]`: `COMPLETED`일 때만 채워짐, 카드 렌더링 대상
> - `PENDING` 수신 시: 프론트는 일정 interval 후 같은 API를 다시 호출
> - `FAILED` 수신 시: retry 버튼을 노출하고 polling을 중단

**Response `404`**

```json
{ "success": false, "message": "감상문을 찾을 수 없습니다." }
```

---

### POST /api/user-reviews/{id}/retry

> 호출 주체: ReviewBasedRecommendPage
> FAILED 상태의 감상문 추천을 사용자가 명시적으로 재시도한다.

**Request**

```
POST /api/user-reviews/42/retry
```

**Response `200`**

```json
{
  "success": true,
  "message": "추천 재시도를 시작했습니다.",
  "data": null
}
```

> 프론트는 retry 성공 후 `GET /api/user-reviews/{id}` polling을 재개한다.
> PENDING 또는 COMPLETED 상태에서의 retry 요청 동작은 백엔드 정책을 따른다.

---

## 3. Recommendation API

### POST /recommend/by-review

> - 호출 주체: Spring Boot → FastAPI (아웃바운드)
> - 감상문 저장 트랜잭션 커밋 후 `RecommendationEventListener`가 `@Async` + `AFTER_COMMIT`으로 호출한다.
> - 실패해도 감상문 저장 트랜잭션에 영향 없음 — `AiRecommendationClient` 내부에서 catch 처리.

**Request**

```
POST {FASTAPI_BASE_URL}/recommend/by-review
Content-Type: application/json
```

```json
{
  "review_id": 42,
  "review_content": "처음 들었을 때의 그 고요함이 아직도 기억난다."
}
```

| 필드 | 설명 |
|------|------|
| review_id | `user_reviews.id` — FastAPI가 콜백 시 `reviewId` path variable로 사용 |
| review_content | 감상문 본문 — 임베딩 및 유사도 계산에 사용 |

**Response `202 Accepted`**

> - 이 응답은 추천 처리 시작 확인용이다.
> - 현재 계약상 Spring은 응답 body를 비즈니스 데이터로 사용하지 않으므로, FastAPI는 `202 Accepted` 상태만 반환해도 된다.
> - body를 반환하더라도 임베딩 벡터, 유사도 검색 결과, 추천 사유는 포함하지 않는다.
> - FastAPI는 추천 처리를 완료한 뒤 `POST /api/user-reviews/{reviewId}/recommendations` 콜백으로 처리 결과(`COMPLETED`/`FAILED`)를 전달한다.
> - Spring은 FastAPI 시작 요청 자체가 실패하면 자체 정책에 따라 `recommendationStatus=FAILED`로 전이한다.

---

### POST /api/user-reviews/{reviewId}/recommendations

> 호출 주체: FastAPI AI 서버 → Spring Boot (인바운드 콜백)
> 추천 처리 결과를 통지한다.
> `status=COMPLETED`이면 추천 앨범 batch를 저장하고, `status=FAILED`이면 추천 저장 없이 감상문 상태를 FAILED로 전이한다.
> 추천 앨범 중복은 DB UNIQUE 제약으로 조용히 스킵.

**Request**

```
POST /api/user-reviews/42/recommendations
Content-Type: application/json
```

```json
{
  "status": "COMPLETED",
  "recommendations": [
    {
      "albumId": "00000000-0000-0000-0000-000000000101",
      "recommendationScore": 0.9423,
      "recommendationReason": "모달 재즈 특유의 정적인 분위기가 유사합니다."
    },
    {
      "albumId": "00000000-0000-0000-0000-000000000205",
      "recommendationScore": 0.8812,
      "recommendationReason": "느린 템포와 서정적인 피아노 라인이 공통적입니다."
    }
  ]
}
```

| 필드 | 필수 | 설명 |
|------|------|------|
| status | Y | `COMPLETED` 또는 `FAILED` |
| recommendations | Y | `COMPLETED`일 때 TOP K 추천 목록, `FAILED`일 때 빈 배열 |
| recommendations[].albumId | COMPLETED일 때 Y | `v_embedding_with_album.album_id` (= `embedding_vectors.id` UUID 문자열) |
| recommendations[].recommendationScore | COMPLETED일 때 Y | 추천 점수 (precision=5, scale=4) |
| recommendations[].recommendationReason | COMPLETED일 때 Y | 추천 사유 |
| errorCode | FAILED일 때 Y | 실패 원인 코드 |
| message | FAILED일 때 Y | 실패 설명 |

**Failure Request 예시**

```json
{
  "status": "FAILED",
  "errorCode": "NO_CANDIDATES",
  "message": "추천 후보가 없습니다.",
  "recommendations": []
}
```

**Response `200`**

```
(body 없음 — ResponseEntity<Void>)
```

> 이 응답은 Spring Boot가 FastAPI 콜백 요청을 처리한 뒤 FastAPI에게 반환하는 HTTP 응답이다.
> FastAPI는 Spring의 응답 body를 파싱하지 않고, 2xx 여부만 성공 기준으로 사용한다.

---

## 4. CriticsReview API


### GET /api/critics

> 호출 주체: CriticsReviewPage
> GPT 요약이 완료된 전문가 리뷰 목록을 페이지네이션으로 반환한다.
> Response DTO: `Page<CriticsReviewSummaryResponse>`

**Request**

```
GET /api/critics?page=0&size=10
```

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| page | 0 | 페이지 번호 (0-based) |
| size | 10 | 페이지 크기 |

**Response `200`**

```json
{
  "content": [
    {
      "id": "uuid-1234",
      "title": "Kind of Blue Review",
      "reviewer": "AllAboutJazz",
      "date": "2024-01-15",
      "reviewSummary": "GPT 요약 내용..."
    }
  ],
  "totalElements": 15,
  "totalPages": 2,
  "number": 0,
  "size": 10,
  "last": false
}
```

> 프론트 의존 필드
> - `content[]`: `CriticsReviewSummaryResponse` 목록
> - `last`: `true`이면 무한 스크롤 종료
> - `number`: 다음 요청 시 `page=number+1`

---

### GET /api/critics/{id}

> 호출 주체: CriticsReviewPage (상세)
> 전문가 리뷰 단건을 반환한다.
> Response DTO: `CriticsReviewResponse`

**Request**

```
GET /api/critics/uuid-1234
```

**Response `200`**

```json
{
  "id": "uuid-1234",
  "title": "Kind of Blue Review",
  "reviewer": "AllAboutJazz",
  "date": "2024-01-15",
  "content": "원문 내용...",
  "reviewSummary": "GPT 요약 내용...",
  "url": "https://www.allaboutjazz.com/...",
  "createdAt": "2026-05-01T09:00:00"
}
```

**Response `404`**

```json
{ "success": false, "message": "리뷰를 찾을 수 없습니다." }
```
