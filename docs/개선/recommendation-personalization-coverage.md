# 추천 개인화 커버리지 개선

## 한눈에 보기

| | 개선 전 | 개선 후 |
|---|---|---|
| 취향 벡터 커버리지 | `album_reference` embedding이 있는 과거 감상만 반영 (실제 12.5%) | embedding이 없는 과거 감상도 `mb_album` 메타로 추가 반영 |
| 후보 정렬 | vector similarity 순서 그대로 | vector score 80% + 아티스트/장르/연대 meta score 20% |
| user_id 전달 | FastAPI 요청에 없음 | Spring → FastAPI 요청에 user_id 포함 |

**핵심 문제:** 사용자가 선택한 MusicBrainz 앨범이 추천 후보 DB(`album_reference`)와 12.5%만 연결되어, 대부분의 경우 개인화 없이 추천이 동작하고 있었다.

**해결 방향:** embedding 연결이 없는 앨범도 MusicBrainz 메타(아티스트, 장르, 연대)를 추출해 후보 재순위에 반영함으로써, 커버리지와 무관하게 개인화 신호를 활용한다.

---

## 문제 상황

클러스터링 기반 추천을 추가하면서 사용자의 과거 감상 앨범 embedding을 평균내어 취향 벡터를 만들 수 있게 되었다.

하지만 실제 운영 데이터에서는 사용자가 선택한 MusicBrainz 앨범이 AllAboutJazz 기반 추천 후보 DB인 `album_reference`와 항상 연결되지 않는다.

당시 추천 개인화 흐름:

```text
user_reviews.mb_album_gid
    ↓
album_reference.mb_release_group_id
    ↓
album_reference.embedding
    ↓
TasteVectorService에서 사용자 취향 벡터 생성
```

이 연결이 실패하면 FastAPI는 사용자의 기존 감상 이력을 반영하지 못하고, 신규 감상문 embedding만으로 검색한다.

---

## 완료된 개선

### 1. FastAPI 요청에 user_id 전달

Spring Boot가 FastAPI 추천 요청을 보낼 때 `user_id`를 함께 전달하도록 변경했다.

관련 파일:
- `backendJava/src/main/java/shop/jazzmate/jazzmateshop/recommendation/client/AiRecommendationClient.java`
- `backendPython/app/schemas/recommendation.py`

### 2. 사용자 기존 감상 앨범 embedding 조회

`UserListenedAlbumRepository`를 추가했다.

역할:
- `user_id`로 `user_reviews` 조회
- `mb_album_gid`가 있는 감상문만 사용
- 중복 앨범 제거
- `album_reference.mb_release_group_id`로 연결
- `album_reference.embedding`이 있는 앨범만 반환
- embedding 차원이 1536이 아니면 오류 처리

관련 파일:
- `backendPython/app/repositories/user_listened_album_repository.py`
- `backendPython/tests/unit/test_user_listened_album_repository.py`

### 3. 취향 벡터 생성

`TasteVectorService`를 추가했다.

현재 계산식:

```text
query_vector = review_embedding * 0.6 + user_taste_vector * 0.4
```

`user_taste_vector`는 사용자의 기존 감상 앨범 embedding 평균이다.

기존 감상 앨범 embedding이 없으면 신규 감상문 embedding을 그대로 사용한다.

관련 파일:
- `backendPython/app/services/taste_vector_service.py`
- `backendPython/tests/unit/test_taste_vector_service.py`

### 4. 추천 서비스 연결

`RecommendationService`에 사용자 취향 벡터 흐름을 연결했다.

처리 순서:

```text
감상문 embedding 생성
    ↓
사용자 기존 감상 앨범 embedding 조회
    ↓
기존 감상 앨범이 있으면 취향 벡터와 블렌딩
    ↓
match_albums() 검색
    ↓
추천 사유 생성
    ↓
Spring callback
```

관련 파일:
- `backendPython/app/services/recommendation_service.py`
- `backendPython/tests/unit/test_recommendation_service.py`

---

## 검증 결과

### 자동 테스트

FastAPI 테스트:

```text
79 passed, 1 warning
```

Spring Boot 테스트:

```text
BUILD SUCCESSFUL
```

### 운영 데이터 연결률

실제 Supabase 데이터 기준으로 `user_reviews.mb_album_gid`가 `album_reference.mb_release_group_id`와 얼마나 연결되는지 확인했다.

```text
mb_album_gid가 있는 감상문: 8건
서로 다른 mb_album_gid: 8개
album_reference.mb_release_group_id에서 찾힌 앨범: 2개
embedding까지 있는 앨범: 1개

연결률: 25.0%
실제 취향 벡터 적용 가능률: 12.5%
```

의미:
- 사용자가 선택한 MusicBrainz 앨범 8개 중 2개만 AllAboutJazz 추천 후보 DB와 연결된다.
- 실제 취향 벡터 계산에 사용할 수 있는 embedding은 1개뿐이다.
- 현재 개인화 로직은 테스트상 동작하지만, 운영 데이터에서는 fallback 비율이 높다.

---

## 원인 분석

### 데이터 커버리지 차이

현재 두 데이터셋의 범위가 다르다.

| 데이터 | 범위 | 용도 |
|---|---|---|
| `mb_album` | MusicBrainz release group 기반 재즈 메타 | 사용자 앨범 검색/선택 |
| `album_reference` | AllAboutJazz 리뷰 기반 앨범 후보 | 추천 후보 검색, embedding 검색 |

사용자는 `mb_album`에서 넓은 범위의 발매물을 선택할 수 있지만, 추천 후보 embedding은 AllAboutJazz에서 수집된 앨범에만 있다.

따라서 모든 `mb_album.gid`가 `album_reference.mb_release_group_id`로 연결될 수 없다.

### 매칭 실패와 데이터 부재 구분

연결되지 않은 `mb_album_gid`를 대상으로 `album_reference` 유사 후보를 확인했다.

유사 후보 없음:

```text
The Cannonball Adderley Quintet - Autumn Leaves
Sarah Vaughan - Misty
The Dave Brubeck Quartet - Take Five
Miles Davis - Blue Miles
Wayne Shorter - Speak No Evil
```

유사 후보 있음:

```text
Art Blakey & The Jazz Messengers - Moanin'
→ 후보: Kenny Washington - Moanin'
```

현재 샘플 기준으로는 매칭 로직 오류보다 `album_reference`에 해당 발매물이 없는 문제가 더 크다.

---

## 검토한 개선 방향

### 1. 입력 가능한 앨범을 album_reference로 제한

기각.

장점:
- 취향 벡터 적용률은 높아진다.

단점:
- 사용자가 감상문을 작성할 수 있는 대상이 AllAboutJazz 수집 데이터로 제한된다.
- MusicBrainz 검색을 도입한 의미가 줄어든다.
- 싱글, EP, 스탠더드명 기반 release group, AllAboutJazz에 없는 앨범 감상을 반영할 수 없다.

### 2. album_reference 매칭 로직만 먼저 개선

보류.

장점:
- AllAboutJazz에 있는데 MusicBrainz 매칭이 실패한 일부 케이스를 회복할 수 있다.

한계:
- AllAboutJazz에 없는 발매물은 여전히 embedding을 만들 수 없다.
- 현재 샘플에서는 매칭 실패보다 데이터 커버리지 차이가 더 큰 원인으로 보인다.

### 3. MusicBrainz 메타 기반 fallback 개인화

채택 및 구현 완료.

핵심:
- embedding이 있는 과거 감상 앨범은 기존처럼 취향 벡터에 반영한다.
- embedding이 없는 과거 감상 앨범도 `mb_album` 메타로 반영한다.
- 최종 후보를 vector similarity만으로 확정하지 않고, artist / genres / era 기반 점수를 더해 재순위한다.

---

## 구현된 개선안

### mb 메타 기반 재순위

`match_albums()`에서 후보를 넉넉히 가져온 뒤, 사용자 과거 감상 이력의 MusicBrainz 메타와 후보 앨범 메타를 비교해 최종 순위를 조정한다.

현재 추천 개인화 흐름:

```text
신규 감상문 embedding 생성
    ↓
[취향 벡터 경로] user_reviews.mb_album_gid
    → album_reference.mb_release_group_id
    → album_reference.embedding
    → TasteVectorService: 감상문 embedding 60% + 취향 벡터 40% 블렌딩
    ↓ (embedding 없는 과거 감상은 이 경로를 건너뜀)
candidate_pool_size(50) 후보 조회
    ↓
[메타 재순위 경로] user_reviews.mb_album_gid
    → mb_album.gid (embedding 없는 과거 감상도 포함)
    → 아티스트 / 장르 / 연대 취향 프로필 생성
    ↓
후보 album_reference.id → mb_release_group_id → mb_album 메타 조회
    ↓
vector score 80% + meta score 20% 로 최종 top_k 재순위
```

구현 점수:

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

테스트:
- `backendPython/tests/unit/test_user_taste_metadata_repository.py`
- `backendPython/tests/unit/test_album_metadata_repository.py`
- `backendPython/tests/unit/test_recommendation_rerank_service.py`
- `backendPython/tests/unit/test_recommendation_service.py`

---

## 구현 시 고려사항

- `album_reference` 후보에 MusicBrainz 메타가 없는 경우 기존 vector score만 사용한다.
- 메타 점수는 추천을 뒤집기보다 동률/근접 후보 재순위 용도로 시작한다.
- 특정 아티스트 반복 추천이 과도해지지 않도록 artist 가중치는 낮게 둔다.
- 사용자 감상 이력이 적을 때는 메타 점수 영향도를 낮춘다.
- 운영 검증에서는 기존 감상 이력이 있는 사용자와 없는 사용자를 분리해 비교한다.
- 기존 감상 embedding 조회 실패(`RepositoryError`)와 메타 조회 실패(`RepositoryError`)는 모두 추천 실패로 처리하고 `FAILED` 콜백을 전송한다.

---

## 검증

FastAPI 테스트:

```text
98 passed, 1 warning
```

검증한 케이스:
- embedding 이력이 있으면 기존 취향 벡터 사용
- embedding이 없는 이력도 메타 점수에 반영
- 이력이 없으면 기존 vector 검색과 동일
- 후보 메타가 없으면 vector score만 사용
- 메타 조회 실패(`RepositoryError`) 시 `FAILED` 콜백 전송
- 기존 감상 embedding 조회 실패(`RepositoryError`) 시 `FAILED` 콜백 전송

## 다음 작업

1. 운영 데이터 기준 추천 결과 비교
2. `vector_score` / `meta_score` 가중치 조정
3. 특정 아티스트 반복 추천 여부 확인
4. 후보 pool size 50의 처리 시간 영향 측정
5. DB에도 `recommend_album.album_artist`, `recommend_album.album_title` `NOT NULL` 제약 추가를 검토한다.
