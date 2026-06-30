# 감상문 기반 추천과 개인화 보조 신호

## 한눈에 보기

추천의 기준은 항상 사용자가 현재 작성한 감상문이다.

FastAPI는 감상문 본문을 embedding으로 변환하고, 이 벡터를 중심으로 `album_reference` 후보를 검색한다. 개인화는 추가적으로 '사용자의 이전 감상 이력'과 '선택 앨범 메타데이터'를 보조 신호로 더해 후보 순서를 조정한다.

| 구분 | 역할 | 적용 방식 |
|---|---|---|
| 현재 감상문 embedding | 추천의 1순위 기준 | `review_content`를 embedding해 vector search query로 사용 |
| 과거 감상문 embedding | 의미 기반 취향 보정 | `user_reviews.review_embedding` 평균을 현재 감상문 embedding과 블렌딩 |
| 감상 앨범 embedding | 연결 가능한 경우의 앨범 취향 보정 | 사용자가 선택한 `mb_album_gid`가 `album_reference`와 연결될 때 과거 감상문 embedding과 함께 블렌딩 |
| MusicBrainz 메타 | 커버리지 보완용 재순위 | artist / genre / era 기반 meta score로 후보 재순위 |

핵심 원칙:
- 현재 감상문 embedding이 추천의 기준이다.
- 과거 감상문 embedding은 사용자의 언어적 취향을 누적하는 보조 신호다.
- 앨범 embedding과 MusicBrainz 메타는 감상문 기반 추천을 보완하는 `+@` 신호다.
- MusicBrainz 앨범이 `album_reference`에 없어도 감상문 embedding 기반 추천은 계속 동작해야 한다.

---

## 추천 기준

사용자가 감상문을 작성하면 Spring Boot는 감상문 저장 후 FastAPI에 추천을 비동기로 요청한다.

```text
POST /recommend/review
{
  review_id,
  review_content,
  user_id
}
```

FastAPI는 `review_content`를 OpenAI embedding 모델로 변환한다.

```text
review_content
    ↓
current_review_embedding
    ↓
album_reference vector search
```

이 벡터가 추천의 1차 기준이다.

사용자가 어떤 앨범을 선택했는지, 그 앨범이 `album_reference`에 연결되는지, 사용자의 과거 감상 이력이 충분한지는 모두 보조 조건이다. 이 조건들이 없더라도 현재 감상문 embedding만으로 추천은 성립한다.

---

## 개인화 신호 설계

### 1. 과거 감상문 embedding

추천 완료 시 FastAPI는 현재 감상문의 embedding을 Spring Boot 콜백에 포함한다.

```text
FastAPI 추천 완료
    ↓
POST /api/user-reviews/{reviewId}/recommendations
    - recommendations[]
    - reviewEmbedding
    ↓
Spring Boot
    ↓
user_reviews.review_embedding 저장
```

이후 같은 사용자가 새 감상문을 작성하면 FastAPI는 `user_id`로 과거 감상문 embedding을 조회한다.

```text
user_reviews.user_id
    ↓
user_reviews.review_embedding IS NOT NULL
    ↓
previous_review_embeddings
```

`TasteVectorService`는 과거 감상문 embedding의 평균을 사용자 취향 벡터로 보고, 현재 감상문 embedding과 블렌딩한다.

```text
query_vector =
  current_review_embedding * 0.6
+ user_taste_vector        * 0.4
```

과거 감상문 embedding이 없으면 현재 감상문 embedding을 그대로 사용한다.

이 신호의 장점:
- 사용자가 직접 작성한 문장에 담긴 분위기, 감정, 선호 표현을 반영한다.
- 사용자가 선택한 앨범이 `album_reference`와 연결되지 않아도 누적된다.
- 추천 후보 DB의 앨범 커버리지와 독립적으로 개인화가 가능하다.

관련 파일:
- `backendPython/app/repositories/user_listened_album_repository.py`
- `backendPython/app/services/taste_vector_service.py`
- `backendPython/app/services/recommendation_service.py`
- `backendJava/src/main/java/shop/jazzmate/jazzmateshop/recommendation/RecommendAlbumService.java`
- `backendJava/src/main/java/shop/jazzmate/jazzmateshop/userReview/entity/UserReview.java`

### 2. 감상 앨범 embedding

사용자가 감상문 작성 시 선택한 MusicBrainz 앨범이 `album_reference.mb_release_group_id`와 연결될 수 있다면, 해당 후보 DB의 앨범 embedding도 취향 보조 신호로 사용한다.

```text
user_reviews.mb_album_gid
    ↓
album_reference.mb_release_group_id
    ↓
album_reference.embedding
```

다만 이 신호는 선택적이어야 한다.

`mb_album`은 MusicBrainz release group 기반의 넓은 앨범 카탈로그이고, `album_reference`는 AllAboutJazz 수집 리뷰 기반의 추천 후보 DB다. 두 데이터셋의 범위가 다르기 때문에 모든 사용 앨범이 `album_reference`에 연결되지는 않는다.

운영 샘플에서 확인한 연결률:

```text
mb_album_gid가 있는 감상문: 8건
서로 다른 mb_album_gid: 8개
album_reference.mb_release_group_id에서 찾힌 앨범: 2개
embedding까지 있는 앨범: 1개

연결률: 25.0%
embedding 사용 가능률: 12.5%
```

따라서 감상 앨범 embedding은 추천의 기준이 아니라 `연결되는 경우에만 추가되는 보조 신호`로 취급한다. 연결된 embedding은 과거 감상문 embedding과 함께 개인화 embedding 목록에 포함되고, `TasteVectorService`에서 현재 감상문 embedding과 블렌딩된다.

이 신호의 용도:
- 사용자가 실제로 감상한 앨범이 추천 후보 DB에 있을 때 취향 정보를 강화한다.
- 감상문 텍스트와 별개로 앨범 자체의 리뷰 요약 embedding을 반영할 수 있다.
- 연결 실패 시 현재 감상문 embedding과 과거 감상문 embedding 경로로 fallback한다.

### 3. MusicBrainz 메타

앨범 embedding 연결률이 낮더라도 `mb_album` 자체의 메타데이터는 더 넓게 사용할 수 있다.

사용하는 메타:
- `artist_name`
- `genres`
- `first_release_year`

FastAPI는 vector search로 후보를 최종 추천 개수보다 넉넉히 가져온 뒤, 사용자 과거 감상 이력의 MusicBrainz 메타와 후보 앨범 메타를 비교해 재순위한다.

```text
query_vector로 candidate_pool_size 후보 조회
    ↓
user_reviews.mb_album_gid → mb_album 메타 조회
    ↓
candidate.album_id → album_reference.mb_release_group_id → mb_album 메타 조회
    ↓
vector score + meta score로 최종 top_k 재순위
```

현재 점수식:

```text
final_score =
  vector_similarity * 0.80
+ meta_score        * 0.20

meta_score =
  artist_score * 0.25
+ genre_score  * 0.55
+ era_score    * 0.20
```

세부 기준:

| 점수 | 기준 |
|---|---|
| `artist_score` | 사용자가 과거에 감상한 아티스트와 후보 아티스트 일치 또는 유사 |
| `genre_score` | `mb_album.genres` 교집합 비율 |
| `era_score` | `first_release_year` 차이가 작을수록 높은 점수 |

관련 파일:
- `backendPython/app/repositories/user_taste_metadata_repository.py`
- `backendPython/app/repositories/album_metadata_repository.py`
- `backendPython/app/services/recommendation_rerank_service.py`
- `backendPython/app/services/recommendation_service.py`

---

## 전체 처리 흐름

```text
사용자 감상문 작성
    ↓
Spring Boot: user_reviews 저장, recommendation_status=PENDING
    ↓
Spring Boot → FastAPI: review_id, review_content, user_id 전달
    ↓
FastAPI: current_review_embedding 생성
    ↓
[개인화 보조 1]
user_reviews.review_embedding 조회
    → 과거 감상문 embedding 평균
user_reviews.mb_album_gid → album_reference.embedding 조회
    → 연결 가능한 감상 앨범 embedding
    → 현재 감상문 embedding 60% + 개인화 embedding 평균 40%
    ↓
album_reference vector search
    ↓
[개인화 보조 2]
감상 앨범이 album_reference에 연결되면 앨범 embedding을 개인화 embedding에 포함
    ↓
[개인화 보조 3]
MusicBrainz artist / genre / era 메타로 후보 재순위
    ↓
추천 사유 생성
    ↓
FastAPI → Spring Boot callback
    - recommendations[]
    - reviewEmbedding
    ↓
Spring Boot: 추천 결과 저장, review_embedding 저장, recommendation_status=COMPLETED
```

---

## fallback 정책

개인화 신호는 추천의 필수 조건이 아니다.

| 상황 | 처리 |
|---|---|
| 과거 감상문 embedding 없음 | 현재 감상문 embedding만으로 검색 |
| 감상 앨범이 `album_reference`에 없음 | 앨범 embedding 보조 신호 생략 |
| MusicBrainz 메타 없음 | vector score 순서 유지 |
| 후보 앨범 메타 없음 | 해당 후보는 meta score 없이 평가 |
| embedding 생성 실패 | 추천 실패, `FAILED` 콜백 |
| vector search 실패 | 추천 실패, `FAILED` 콜백 |

이 정책의 목적은 추천 기준을 안정적으로 유지하는 것이다.

현재 감상문 embedding이 생성되고 `album_reference` vector search가 가능하면 추천은 진행한다. 과거 이력, 앨범 연결, 메타데이터는 있으면 더하는 신호로만 사용한다.

---

## 데이터셋 역할 구분

| 데이터 | 범위 | 추천에서의 역할 |
|---|---|---|
| `user_reviews.review_content` | 사용자가 현재 작성한 감상문 | 추천 query의 원문 |
| `user_reviews.review_embedding` | 추천 완료된 과거 감상문 embedding | 의미 기반 사용자 취향 벡터 |
| `album_reference` | AllAboutJazz 리뷰 기반 추천 후보 | vector search 대상 |
| `album_reference.embedding` | 평론가 리뷰 요약 기반 앨범 embedding | 후보 검색 및 연결 가능한 앨범 보조 신호 |
| `mb_album` | MusicBrainz release group 기반 재즈 메타 | 사용자 앨범 선택, 메타 기반 재순위 |

중요한 구분:
- `album_reference`는 추천 후보 DB다.
- `mb_album`은 사용자가 감상 앨범을 선택하는 넓은 메타 DB다.
- 두 데이터셋은 1:1로 연결되지 않는다.
- 그래서 추천의 주 기준은 특정 앨범 연결이 아니라 감상문 embedding이어야 한다.

---

## 구현 시 고려사항

- 현재 감상문 embedding은 매 추천 요청마다 새로 생성한다.
- 추천 성공 콜백에는 `reviewEmbedding`을 포함해 다음 추천의 개인화 신호로 누적한다.
- 과거 감상문 embedding은 같은 `user_id`의 저장된 embedding만 사용한다.
- 사용자의 과거 감상문 수가 적을 때는 현재 감상문 embedding의 영향이 더 커야 한다.
- 앨범 embedding은 연결 가능한 경우에만 반영하고, 연결률을 추천 가능 여부로 해석하지 않는다.
- MusicBrainz 메타 점수는 추천 결과를 과도하게 뒤집기보다 근접 후보 재순위 용도로 사용한다.
- 특정 아티스트 반복 추천이 과도해지지 않도록 artist 가중치는 낮게 둔다.

---

## 검증

FastAPI 테스트:

```text
98 passed, 1 warning
```

검증한 케이스:
- 감상문 embedding 생성 후 vector search 수행
- 과거 감상문 embedding이 있으면 취향 벡터로 블렌딩
- 과거 감상문 embedding이 없으면 현재 감상문 embedding만 사용
- 추천 완료 콜백에 `reviewEmbedding` 포함
- `reviewEmbedding`을 Spring Boot에서 `user_reviews.review_embedding`에 저장
- MusicBrainz 메타가 있으면 후보 재순위
- 후보 메타가 없으면 vector score 유지
- embedding 생성 실패 시 `FAILED` 콜백
- vector search 실패 시 `FAILED` 콜백

---

## 다음 작업

1. 운영 데이터에서 `user_reviews.review_embedding` 저장률을 측정한다.
2. 사용자별 과거 감상문 embedding 개수 분포를 확인한다.
3. 현재 감상문 0.6 / 과거 취향 벡터 0.4 가중치를 추천 품질 기준으로 조정한다.
4. 과거 감상문 embedding과 감상 앨범 embedding을 동일 가중 평균으로 둘지, 신호별 가중치를 분리할지 결정한다.
5. MusicBrainz meta score 20%가 추천 결과를 과도하게 바꾸지 않는지 검증한다.
6. 특정 아티스트 반복 추천 여부를 운영 결과로 확인한다.
