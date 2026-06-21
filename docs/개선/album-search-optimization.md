# 앨범 검색 API 성능 최적화

## 문제 상황

`GET /api/musicbrainz/albums/search` — 감상문 작성 시 앨범명/아티스트명 검색에 사용하는 API.

### 문제 쿼리 (개선 전)

```java
// MusicBrainzAlbumRepository.java
@Query("""
        SELECT a FROM MusicBrainzAlbum a
        WHERE LOWER(a.name) LIKE LOWER(CONCAT('%', :albumName, '%'))
          AND LOWER(a.artistName) LIKE LOWER(CONCAT('%', :artistName, '%'))
        ORDER BY a.firstReleaseYear ASC
        """)
List<MusicBrainzAlbum> search(...);
```

### 문제점

| # | 문제 | 원인 |
|---|------|------|
| 1 | B-Tree 인덱스 미사용 | 양측 와일드카드 `'%keyword%'` — B-Tree는 prefix 검색만 가능 |
| 2 | 함수형 인덱스 우회 | `LOWER()` 래핑 — `idx_mb_album_name` (B-Tree) 완전 무력화 |
| 3 | artist_name 인덱스 완전 없음 | 013 마이그레이션에서 컬럼만 추가, B-Tree/GIN 모두 미생성 — name보다 더 심각한 Seq Scan |
| 4 | 결과 상한 없음 | LIMIT 없음 — 전체 매칭 행 반환 |

### 데이터 규모 및 실측 성능 (개선 전)

- mb_album: **약 129,000건** (재즈 태그 앨범)
- 실측 조건: `EXPLAIN ANALYZE`, 키워드 "love" (최악 케이스), `LIMIT 20`, GIN 인덱스 없는 상태에서 Seq Scan 강제
  - Seq Scan — 136,593행 전부 읽고 3,073건 매칭
  - Buffer read: 5,476 블록 (디스크 읽기)
  - Sort Method: top-N heapsort
  - **Execution Time: 675ms**

---

## 검토한 개선안

| 옵션 | 결론 | 이유 |
|------|------|------|
| **pg_trgm GIN 인덱스** | **채택** | `LOWER() LIKE '%x%'` 패턴 직접 지원, 스키마 변경 없음, Supabase 기본 내장 |
| Full-Text Search (tsvector) | 제외 | 고유명사 stemming 왜곡 ("Miles" → "mile") — 아티스트명/앨범명에 부정확 |
| Elasticsearch / OpenSearch | 제외 | 별도 인프라 + 동기화 파이프라인 필요 — 현재 스코프 대비 복잡도 과도 |
| citext 타입 변경 | 제외 | `LOWER()` 문제는 해결하나 `%x%` 양측 와일드카드 문제는 여전히 남음. FK 연관 컬럼 타입 변경 파급 범위 큼 |
| Bloom Filter | 제외 | equality 검색(`=`)에만 동작. `LIKE '%x%'` 범위 검색에는 효과 없음 |
| Prefix 전용 (`LIKE 'x%'`) | 제외 | B-Tree 인덱스 사용 가능하나 "Kind of Blue"를 "Blue"로 검색 불가 — UX 제약 큼 |
| 앱 레벨 캐싱 (Caffeine/Redis) | 보류 | 입력마다 호출하는 구조에서 검색어가 매번 달라 캐시 히트율 낮음. pg_trgm으로 충분하면 불필요 |

## 채택한 개선안

### pg_trgm GIN 인덱스 + LIMIT 20

**pg_trgm 동작 원리**: 텍스트를 3-gram(3글자 단위)으로 분해하여 역색인을 구성한다.

```
"miles" → "mil", "ile", "les"
"blue"  → "blu", "lue"

GIN 역색인
"blu" → [row 88, row 201, ...]
"lue" → [row 88, row 201, ...]
```

검색어도 동일하게 분해 → 역색인 교집합만 읽음.
136,593행 전체 스캔 대신 매칭 행만 골라서 읽는다.

B-Tree가 prefix 검색(`LIKE 'x%'`)만 지원하는 것과 달리, GIN은 `LOWER() LIKE '%x%'` 패턴을 인덱스에서 직접 처리한다.

---

## 변경 내용

### 마이그레이션

파일: `backendJava/migrations/015_add_trgm_index_to_mb_album.sql`

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_mb_album_name_trgm
    ON mb_album USING GIN (LOWER(name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_mb_album_artist_name_trgm
    ON mb_album USING GIN (LOWER(artist_name) gin_trgm_ops);
```

**실행**: Supabase Dashboard > SQL Editor에서 직접 실행 (자동화 금지)

### Repository 쿼리 (개선 후)

```java
@Query(value = """
        SELECT * FROM mb_album
        WHERE LOWER(name) LIKE LOWER(CONCAT('%', :albumName, '%'))
          AND (:artistName = '' OR LOWER(artist_name) LIKE LOWER(CONCAT('%', :artistName, '%')))
        ORDER BY first_release_year ASC
        LIMIT 20
        """, nativeQuery = true)
List<MusicBrainzAlbum> search(...);
```

변경 포인트:
- **Native Query 전환**: JPQL → Native SQL. Hibernate 변환 없이 PostgreSQL에 직접 전달되어 GIN 인덱스 플래너가 정확히 동작
- **LIMIT 20**: 드롭다운 UI 기준 실용적 상한. 전체 매칭 행 반환 방지
- **artistName 단락 조건**: `:artistName = '' OR ...` — artistName 빈 문자열 시 해당 필터 스킵

### Controller (개선 후)

```java
@RequestParam(required = false, defaultValue = "") String artistName
```

`artistName`을 선택적 파라미터로 변경. albumName만으로도 검색 가능.

---

## 성능 비교

측정 조건: 키워드 "love" (최악 케이스), LIMIT 20, 동일 조건에서 비교

| | 개선 전 (Seq Scan 강제) | 개선 후 (GIN) |
|--|------------------------|--------------|
| Execution Time | **675ms** | **9ms** |
| 스캔 방식 | 136,593행 전체 스캔 후 필터 | GIN으로 위치 파악 후 Heap 접근 |
| Buffer read (디스크) | 5,476 블록 | 0 블록 (캐시) |
| Sort Method | top-N heapsort | top-N heapsort |
| **개선 배율** | — | **75배** |

> GIN 없이 LIMIT 없는 쿼리(478ms)와 비교하면 조건이 달라 부정확하다.
> 공정한 비교는 동일한 LIMIT 20 조건 기준: **675ms → 9ms**.

---

## 한계

- **2글자 이하 키워드**: pg_trgm은 3-gram 단위라 2자 미만 키워드는 Seq Scan fallback. 재즈 앨범명 특성상 실용적 문제 없음
- **GIN 인덱스 크기**: 인덱스 2개 합산 약 20~40MB 추가 예상 (Supabase 허용 범위)

---

## 검증 방법

마이그레이션 실행 후 Supabase SQL Editor에서 아래 쿼리로 인덱스 활용 여부 확인:

```sql
EXPLAIN ANALYZE
SELECT * FROM mb_album
WHERE LOWER(name) LIKE LOWER('%blue%')
  AND LOWER(artist_name) LIKE LOWER('%miles%')
ORDER BY first_release_year ASC
LIMIT 20;
```

개선 후 기대 결과: `Bitmap Index Scan on idx_mb_album_name_trgm` 확인
