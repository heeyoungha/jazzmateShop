# JazzmateShop — DTO / Entity 명세

> 실제 코드 기준: `backendJava/src/main/java/shop/jazzmate/jazzmateshop/`
> 플로우별 사용처: `SDD.md` 참조

---

## 목차

- [Request DTO](#request-dto)
  - [UserReviewRequest](#userreviewrequest)
  - [RecommendAlbumBatchRequest](#recommendalbumbatchrequest)
- [Response DTO](#response-dto)
  - [UserReviewCreateResponse](#userreviewcreateresponse)
  - [UserReviewResponse](#userreviewresponse)
  - [UserReviewSummaryResponse](#userreviewsummaryresponse)
  - [CriticsReviewSummaryResponse](#criticsreviewsummaryresponse)
  - [CriticsReviewResponse](#criticsreviewdetailresponse)
  - [ApiResponse](#apiresponse)
  - [ErrorResponse](#errorresponse)
- [Entity](#entity)
  - [UserReview](#userreview)
  - [RecommendAlbum](#recommendalbum)
  - [CriticsReview](#criticsreview)
- [Enum](#enum)
  - [RecommendationStatus](#recommendationstatus)
- [Event Record](#event-record)
  - [RecommendationRequestEvent](#recommendationrequestevent)

---

## Request DTO

### UserReviewRequest

> 사용처: `POST /api/user-reviews` (WriteReviewPage)

| No | 필드 | 타입 | 필수 | 설명 |
|----|------|------|------|------|
| 1 | trackName | String | Y (@NotBlank) | 곡명 |
| 2 | artistName | String | Y (@NotBlank) | 아티스트명 |
| 3 | reviewContent | String | Y (@NotBlank) | 감상문 본문 |
| 4 | rating | BigDecimal | N | 평점 |
| 5 | mood | String | N | 무드 |
| 6 | genre | String | N | 장르 |
| 7 | energyLevel | BigDecimal | N | 에너지 레벨 |
| 8 | bpm | Integer | N | BPM |
| 9 | vocalStyle | String | N | 보컬 스타일 |
| 10 | instrumentation | String | N | 편성 |
| 11 | isPublic | Boolean | N | 공개 여부 |

---

### RecommendAlbumBatchRequest

> 사용처: `POST /api/user-reviews/{reviewId}/recommendations` (FastAPI 콜백)

| No | 필드 | 타입 | 필수 | 설명 |
|----|------|------|------|------|
| 1 | recommendations | List\<Item\> | Y | 추천 앨범 목록 |

**Item**

| No | 필드 | 타입 | 필수 | 설명 |
|----|------|------|------|------|
| 1 | albumId | Integer | Y | v_album_embeddings.album_id (= embedding_vectors.id) |
| 2 | recommendationScore | BigDecimal | Y | 추천 점수 (precision=5, scale=4) |
| 3 | recommendationReason | String | Y | 추천 사유 |

---

## Response DTO

### UserReviewCreateResponse

> 사용처: `POST /api/user-reviews` 응답
> 팩토리: `from(UserReview)`

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | id | Integer | 감상문 ID — 프론트 navigate(`/recommend/${id}`)에 사용 |

---

### UserReviewResponse

> 사용처: `GET /api/user-reviews/{id}` 응답
> 팩토리: `from(UserReview, List<RecommendAlbum>)`

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | review | UserReviewDetail | 감상문 상세 정보 |
| 2 | recommendationStatus | RecommendationStatus | 추천 상태 (PENDING/COMPLETED/FAILED) |
| 3 | hasRecommendations | boolean | 추천 결과 존재 여부 — 프론트 polling 분기에 사용 |
| 4 | recommendations | List\<RecommendAlbumResponse\> | 추천 앨범 목록 (COMPLETED일 때만 채워짐) |

**UserReviewDetail** (inner static class)

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | id | Integer | 감상문 ID — 프론트 navigate(`/recommend/${id}`)에 사용 |
| 2 | userId | String | 유저 ID |
| 3 | trackName | String | 곡명 |
| 4 | artistName | String | 아티스트명 |
| 5 | reviewContent | String | 감상문 본문 |
| 6 | rating | BigDecimal | 평점 |
| 7 | mood | String | 무드 |
| 8 | genre | String | 장르 |
| 9 | energyLevel | BigDecimal | 에너지 레벨 |
| 10 | bpm | Integer | BPM |
| 11 | vocalStyle | String | 보컬 스타일 |
| 12 | instrumentation | String | 편성 |
| 13 | isPublic | Boolean | 공개 여부 |
| 14 | isFeatured | Boolean | 피처드 여부 (기본값 false) |
| 15 | likeCount | Integer | 좋아요 수 (기본값 0) |
| 16 | commentCount | Integer | 댓글 수 (기본값 0) |
| 17 | createdAt | LocalDateTime | 생성일시 |
| 18 | updatedAt | LocalDateTime | 수정일시 |

---

### UserReviewSummaryResponse

> 사용처: `GET /api/user-reviews` Page 응답의 `content[]` 항목 (MyReviewsPage)
> 팩토리: `from(UserReview)`

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | id | Integer | 감상문 ID |
| 2 | trackName | String | 곡명 |
| 3 | artistName | String | 아티스트명 |
| 4 | reviewContent | String | 감상문 본문 |
| 5 | rating | BigDecimal | 평점 |
| 6 | mood | String | 무드 |
| 7 | genre | String | 장르 |
| 8 | createdAt | LocalDateTime | 생성일시 |

---

### CriticsReviewSummaryResponse

> 사용처: `GET /api/critics` Page 응답의 `content[]` 항목 (CriticsReviewPage)
> 팩토리: `from(CriticsReview)`

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | id | UUID | 리뷰 ID |
| 2 | title | String | 리뷰 제목 |
| 3 | reviewer | String | 리뷰어 |
| 4 | date | String | 게재일 |
| 5 | reviewSummary | String | GPT 요약 내용 |

---

### CriticsReviewResponse

> 사용처: `GET /api/critics/{id}` 응답 (CriticsReviewDetailPage)
> 팩토리: `from(CriticsReview)`

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | id | UUID | 리뷰 ID |
| 2 | title | String | 리뷰 제목 |
| 3 | reviewer | String | 리뷰어 |
| 4 | date | String | 게재일 |
| 5 | content | String | 원문 |
| 6 | reviewSummary | String | GPT 요약 내용 |
| 7 | url | String | 원문 URL |
| 8 | createdAt | LocalDateTime | 생성일시 |

---

### ApiResponse

> 사용처: POST 성공 응답 래퍼. 조회 API는 DTO/List를 직접 반환하고, FastAPI 내부 콜백은 body 없음.

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | success | boolean | 항상 true |
| 2 | message | String | 응답 메시지 |
| 3 | data | T | 응답 데이터. 데이터가 없는 POST 성공 응답은 null |

---

### ErrorResponse

> 사용처: 에러 응답 래퍼 (GlobalExceptionHandler)

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | success | boolean | 항상 false |
| 2 | message | String | 에러 메시지 |

---

## Entity

### UserReview

> 테이블: `user_reviews`

| No | 필드 | 컬럼 | 타입 | 기본값 | 설명 |
|----|------|------|------|--------|------|
| 1 | id | id | Integer | SERIAL | PK |
| 2 | userId | user_id | String | - | 유저 ID |
| 3 | trackName | track_name | String | - | 곡명 |
| 4 | artistName | artist_name | String | - | 아티스트명 |
| 5 | reviewContent | review_content | TEXT | - | 감상문 본문 (NOT NULL) |
| 6 | rating | rating | BigDecimal(3,1) | - | 평점 |
| 7 | mood | mood | String | - | 무드 |
| 8 | genre | genre | String | - | 장르 |
| 9 | energyLevel | energy_level | BigDecimal(3,2) | - | 에너지 레벨 |
| 10 | bpm | bpm | Integer | - | BPM |
| 11 | vocalStyle | vocal_style | String | - | 보컬 스타일 |
| 12 | instrumentation | instrumentation | String | - | 편성 |
| 13 | isPublic | is_public | Boolean | - | 공개 여부 |
| 14 | recommendationStatus | recommendation_status | VARCHAR(20) | PENDING | 추천 상태 |
| 15 | isFeatured | is_featured | Boolean | false | 피처드 여부 |
| 16 | likeCount | like_count | Integer | 0 | 좋아요 수 |
| 17 | commentCount | comment_count | Integer | 0 | 댓글 수 |
| 18 | createdAt | created_at | LocalDateTime | @CreationTimestamp | 생성일시 |
| 19 | updatedAt | updated_at | LocalDateTime | @UpdateTimestamp | 수정일시 |

---

### RecommendAlbum

> 테이블: `recommend_album`
> 제약: UNIQUE(user_review_id, album_id) — 중복 시 DB에서 에러, 서비스에서 조용히 스킵

| No | 필드 | 컬럼 | 타입 | 설명 |
|----|------|------|------|------|
| 1 | id | id | Integer | PK (SERIAL) |
| 2 | userReviewId | user_review_id | Integer | 감상문 ID (NOT NULL) |
| 3 | albumId | album_id | Integer | v_album_embeddings.album_id (NOT NULL) |
| 4 | recommendationScore | recommendation_score | BigDecimal(5,4) | 추천 점수 (NOT NULL) |
| 5 | recommendationReason | recommendation_reason | TEXT | 추천 사유 (NOT NULL) |
| 6 | createdAt | created_at | LocalDateTime | @CreationTimestamp |
| 7 | updatedAt | updated_at | LocalDateTime | @UpdateTimestamp |

---

### CriticsReview

> 뷰: `v_review_summary` (읽기 전용)

| No | 필드 | 컬럼 | 타입 | 설명 |
|----|------|------|------|------|
| 1 | id | id | UUID | PK |
| 2 | title | title | String | 리뷰 제목 |
| 3 | reviewer | reviewer | String | 리뷰어 |
| 4 | date | published_date | String | 게재일 |
| 5 | content | content | TEXT | 원문 |
| 6 | reviewSummary | review_summary | TEXT | GPT 요약 (NULL이면 미노출) |
| 7 | url | url | String | 원문 URL |
| 8 | createdAt | created_at | LocalDateTime | 생성일시 |

---

## Enum

### RecommendationStatus

> 위치: `userReview/entity/RecommendationStatus.java`

| No | 값 | 의미 | 전이 조건 |
|----|-----|------|-----------|
| 1 | PENDING | 추천 요청 대기/진행 중 | 감상문 저장 시 기본값, FAILED에서 재요청 시 |
| 2 | COMPLETED | 추천 완료 | FastAPI 콜백 수신 후 저장 완료 시 |
| 3 | FAILED | 추천 실패 | AI 요청 실패 또는 콜백 미수신 시 |

---

## Event Record

### RecommendationRequestEvent

> - 발행: `UserReviewService.createUserReview()` (감상문 저장 후)
> - 수신: `RecommendationEventListener.requestRecommendation()` (AFTER_COMMIT + @Async)

| No | 필드 | 타입 | 설명 |
|----|------|------|------|
| 1 | reviewId | Integer | 감상문 ID |
| 2 | reviewContent | String | 감상문 본문 — FastAPI 추천 요청 payload로 사용 |
