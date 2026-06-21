# Supabase DB 스키마 전체 정리

## 테이블/뷰 목록

```
파이프라인 (데이터 수집)          백엔드 Java (추천 서비스)
─────────────────────────         ─────────────────────────
crawl_targets                     user_reviews
pipeline_batches                  recommend_album
crawl_jobs                        album_reference  ←── 추천 단일 소스
allthatjazz_raw       ←───────────────────────────┘ (raw_id 참조)
processed_summary
embedding_vectors     ←── 파이프라인 이력용 (검색 소스 아님)
error_history
```

---

## 파이프라인 테이블

### crawl_targets
크롤링 대상 URL 마스터 테이블.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| url | TEXT UNIQUE | 크롤링 대상 URL |
| created_at | TIMESTAMPTZ | |

---

### pipeline_batches
파이프라인 1회 실행 단위. 크롤링 → GPT → 임베딩 → VectorDB 전체를 묶는 메타.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| batch_num | BIGSERIAL UNIQUE | 순차 식별자 (동시성 보장) |
| airflow_dag_run_id | TEXT | Airflow DAG Run ID |
| created_at / completed_at / cancelled_at | TIMESTAMPTZ | |

---

### crawl_jobs
URL별 크롤링 작업 진행상황.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| batch_id | UUID FK → pipeline_batches | |
| crawl_target_id | UUID FK → crawl_targets | |
| status | TEXT | pending / running / success / failed / skipped |
| attempt_count | INT | 재시도 횟수 |

---

### allthatjazz_raw
AllAboutJazz에서 크롤링한 원시 리뷰 데이터.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| crawl_job_id | UUID FK (1:1) | |
| title | TEXT | "아티스트: 앨범명" 형식 |
| content | TEXT | 리뷰 본문 |
| album_info | JSONB | { year, label, rating, ... } |
| youtube_info | JSONB | 유튜브 링크 등 |
| personnel | JSONB | 연주자 정보 |
| track_listing | TEXT | 트랙 목록 |
| rating | NUMERIC(2,1) | 평점 |
| reviewer | TEXT | 리뷰어명 |
| published_date | DATE | |
| is_processed | BOOLEAN | GPT 처리 여부 |

---

### processed_summary
GPT로 요약한 결과. 임베딩 생성의 입력값.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| raw_id | UUID FK (1:1) → allthatjazz_raw | |
| summary_text | TEXT | 임베딩 생성용 요약 텍스트 |
| summary_data | JSONB | GPT 응답 전체 |
| model_id | TEXT | 사용 모델 |
| token_usage | JSONB | |

---

### embedding_vectors
임베딩 파이프라인 이력 테이블. 벡터 검색 소스는 album_reference로 이전됨 (007 migration).

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | album_reference.embedding_id가 참조 |
| raw_id | UUID FK → allthatjazz_raw | |
| processed_id | UUID FK → processed_summary | |
| vector_id | TEXT | Qdrant point ID |
| embedding | vector(1536) | pgvector 컬럼 (009 migration에서 추가) |
| dim | INT | 벡터 차원 |
| model_id | TEXT | text-embedding-ada-002 / text-embedding-3-small |

---

### error_history
파이프라인 전 단계 에러 이력 (append-only).

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | |
| stage | TEXT | crawl / gpt / embedding / vectordb |
| batch_id / crawl_job_id / processing_job_id | UUID FK | 단계별 참조 |
| error_type / error_message / error_details | TEXT/JSONB | |

---

### processing_jobs
OpenAI Batch API 작업 관리 (GPT 요약, 임베딩 생성).

stage = gpt / embedding / vectordb 3종류.
각 단계별 전용 통계 컬럼이 있음 (summary_api_*, embedding_api_*, vdb_*).

---

## 백엔드 Java 테이블

### user_reviews
사용자가 작성한 감상문. 추천 요청의 시작점.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| user_id | VARCHAR | |
| review_content | TEXT | 감상문 본문 (임베딩 입력) |
| recommendation_status | VARCHAR | PENDING / COMPLETED / FAILED |
| mood / genre / energy_level 등 | 여러 타입 | 부가 정보 |

---

### recommend_album
AI가 추천한 앨범 결과 저장.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | SERIAL PK | |
| user_review_id | INT FK → user_reviews | |
| album_id | UUID | album_reference.id 참조 |
| recommendation_score | NUMERIC(5,4) | 코사인 유사도 |
| recommendation_reason | TEXT | GPT가 생성한 추천 이유 |
| album_artist | TEXT | 추천 시점 스냅샷 |
| album_title | TEXT | 추천 시점 스냅샷 |

---

### album_reference
추천 단일 소스. AllAboutJazz 앨범 메타 + 임베딩 벡터 + MusicBrainz 보강 데이터 통합.
`v_embedding_with_album` 뷰를 대체함 (007 migration).

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID PK | match_albums()가 반환하는 album_id |
| raw_id | UUID FK (1:1) → allthatjazz_raw | critics_review_id로도 참조됨 |
| embedding_id | UUID FK → embedding_vectors | 파이프라인 이력 역참조 |
| embedding | vector(1536) | text-embedding-3-small 벡터. NULL이면 재임베딩 대상 |
| embedding_model | TEXT | 임베딩 모델 식별자 (text-embedding-3-small로 통일) |
| artist_name | TEXT | title에서 파싱 |
| album_title | TEXT | title에서 파싱 |
| release_year | TEXT | album_info->>'year' |
| record_label | TEXT | album_info->>'label' |
| mb_release_id | UUID | MusicBrainz Release MBID |
| mb_artist_id | UUID | MusicBrainz Artist MBID |
| mb_release_group_id | UUID | MusicBrainz Release Group MBID |
| mb_release_date | TEXT | 발매일 (YYYY / YYYY-MM / YYYY-MM-DD) |
| mb_country | TEXT | 발매 국가 코드 |
| mb_label | TEXT | MusicBrainz 레이블명 |
| mb_cover_art_url | TEXT | Cover Art Archive URL |
| mb_matched | BOOLEAN | MusicBrainz 매칭 완료 여부 |
| mb_match_score | NUMERIC(4,3) | 매칭 신뢰도 (0.000 ~ 1.000) |
| mb_matched_at | TIMESTAMPTZ | MusicBrainz 매칭 실행 시각 |

---

## 뷰 목록

| 뷰 이름 | 역할 | 사용처 |
|---|---|---|
| v_album_embeddings | embedding_vectors + allthatjazz_raw + crawl_targets 조인 | 미사용 (004에서 대체) |
| ~~v_embedding_with_album~~ | ~~embedding_vectors + allthatjazz_raw 조인~~ | **007 migration에서 제거. album_reference로 대체** |
| v_pipeline_status | 배치별 파이프라인 진행 현황 | 모니터링 |
| v_pipeline_statistics | 배치별 크롤링 통계 | 모니터링 |
| v_crawl_progress | 크롤링 진행률 | 모니터링 |
| v_failed_jobs | 실패 작업 목록 | 디버깅 |
| v_error_history | 에러 이력 | 디버깅 |

---

## 함수

### match_albums(query_embedding vector(1536), match_count int)
사용자 감상문 벡터와 앨범 임베딩 코사인 유사도 계산.
`album_reference`를 소스로 pgvector `<=>` 연산자 사용 (007 migration에서 교체).

반환: album_id, album_artist, album_title, critics_review_id, similarity

---

## 데이터 흐름 (현재)

```
사용자 감상문 (user_reviews)
    ↓ FastAPI: 감상문 임베딩 생성
    ↓ rpc('match_albums') 호출
    ↓ album_reference (embedding 컬럼 직접 조회, HNSW 인덱스)
    ↓ 코사인 유사도 상위 N개
    ↓ recommend_album 저장
```

---

## 재임베딩 현황

ada-002로 생성된 벡터 (~11,998개)는 text-embedding-3-small로 재임베딩 후
아래 쿼리로 `album_reference.embedding`을 채워야 함:

```sql
UPDATE album_reference ar
SET
    embedding       = ev.embedding,
    embedding_model = ev.model_id,
    embedding_id    = ev.id
FROM embedding_vectors ev
WHERE ev.raw_id = ar.raw_id
  AND ev.model_id = 'text-embedding-3-small'
  AND ev.embedding IS NOT NULL
  AND ar.embedding IS NULL;
```
