# DB 검색 인덱스 학습 노트

> Java 코드 패턴이 아닌 DB/검색 원리 개념을 다룬다.
> `/explain` 커맨드로 자동 업데이트된다.

최종 업데이트: 2026-06-21 (실측 성능 비교 추가 — 675ms → 9ms, 75배 개선)

---

## 배운 개념 목록

### 인덱스란 무엇인가

책의 "목차"와 같다. 목차 없이 책에서 단어를 찾으려면 전체를 다 읽어야 한다(Seq Scan).
목차가 있으면 해당 페이지만 바로 펼친다(Index Scan).

PostgreSQL 테이블 데이터는 디스크의 **블록(8KB 단위)**에 저장된다.
인덱스는 "어떤 값이 어느 블록에 있는지"를 미리 정리해둔 자료구조다.

```
mb_album 테이블 (블록 단위 저장)
┌──────────────────────────────┐
│ Block 1: row1, row2, row3    │
│ Block 2: row4, row5, ...     │
│ ...                          │
│ Block 9031: row136590, ...   │  ← 총 ~9,031 블록
└──────────────────────────────┘
```

인덱스 없이 `WHERE name LIKE '%love%' LIMIT 20` → 136,593행 전부 읽음 → **675ms** (실측)
인덱스 있으면 → 매칭 블록만 읽음 → **9ms** (실측, 75배 개선)

---

### B-Tree 인덱스 — 정렬된 목차

PostgreSQL/MySQL 모두에서 **기본 인덱스 타입**. `CREATE INDEX` 하면 자동으로 B-Tree.
값을 **정렬된 트리 구조**로 저장한다.

```
B-Tree 내부 구조 (name 컬럼)

              [M]
            /     \
        [B~L]     [N~Z]
        /    \
  [A~E]      [F~L]
    |
"A Love Supreme" → Block 42
"All Blues"      → Block 17
"Blue Train"     → Block 88
```

루트에서 시작해 값을 비교하며 내려가면 O(log N)에 원하는 위치를 찾는다.
12.9만 건이면 약 17번 비교로 위치 특정 가능.

**가능한 것**: 정렬된 구조를 활용하는 검색
- `WHERE name = 'Blue Train'` (정확히 일치)
- `WHERE name LIKE 'Blue%'` (앞이 고정 — prefix 검색, "Blue" 위치부터 순서대로 읽음)
- `WHERE name > 'B'` (범위 검색)
- `ORDER BY name` (이미 정렬되어 있으므로 추가 정렬 불필요)

**불가능한 것**: 앞이 와일드카드인 검색
- `WHERE name LIKE '%blue%'` → "blue"가 어느 위치에 올지 모름 → 트리 시작점을 특정할 수 없음 → 전체 스캔

**쓰기 비용**: INSERT/UPDATE 시 트리 재정렬 필요. GIN보다 빠름.

---

### LOWER()가 인덱스를 무력화하는 이유

`idx_mb_album_name` 인덱스는 `name` 원본값으로 만들어졌다.

```sql
WHERE LOWER(name) LIKE '%love%'
```

PostgreSQL 입장: "인덱스에는 `name` 값이 있는데, 쿼리는 `LOWER(name)` 값을 묻는다. 다른 값이니까 이 인덱스를 쓸 수 없다."

해결책 1: `LOWER(name)`으로 함수형 인덱스를 따로 만든다.
해결책 2 (채택): `LOWER(name) gin_trgm_ops`로 GIN 인덱스를 만들면 처음부터 소문자 기준으로 역색인이 구성된다.

---

### pg_trgm GIN 인덱스 — 3-gram 역색인

**trgm**: trigram. 텍스트를 3글자씩 잘라 저장하는 방식.
**GIN**: Generalized Inverted Index. 역색인(inverted index) 자료구조.
**PostgreSQL 전용** — MySQL에는 없음.

GIN은 "하나의 행이 여러 값을 가지는" 경우에 적합한 인덱스다.
배열(`int[]`), JSON(`jsonb`), 전문 검색(tsvector), pg_trgm 모두 GIN을 사용한다.
공통점: 한 행에서 여러 토큰(3-gram, 단어, 배열 원소)이 나오고, 그걸 역색인으로 관리.

#### 역색인이란

"어떤 단어가 어느 문서에 있는가"를 미리 뒤집어 정리한 것.
검색엔진(Google)이 쓰는 원리와 같다.

```
일반 저장 방식 (행 → 단어)
row 88:  "Blue Train"
row 201: "Kind of Blue"

역색인 방식 (단어 → 행)  ← GIN이 이것
"blu" → [row 88, row 201, ...]
"lue" → [row 88, row 201, ...]
"tra" → [row 88, ...]
```

#### 검색 과정

검색어 "blue" → 3-gram 분해: `"blu"`, `"lue"`
→ GIN에서 각 3-gram이 포함된 행 목록을 찾음
→ 교집합 → 매칭 행만 읽음

```
136,593행 전체 스캔 (개선 전)
        ↓
~수백 행만 읽음 (개선 후)
```

#### LIMIT와 top-N heapsort

LIMIT가 없으면 PostgreSQL은 전체 결과를 정렬한다 (quicksort, 886kB).
LIMIT 20이 있으면 "상위 20건만 추적"하는 top-N heapsort로 전환한다 (36kB).
정렬 메모리가 24배 줄고, 전체를 정렬할 필요가 없어서 훨씬 빠르다.

```
LIMIT 없음: 3,073건 전체 정렬 → quicksort 886kB → 957ms
LIMIT 20:   상위 20건만 추적 → top-N heapsort 36kB → 9ms
```

GIN 인덱스만큼이나 LIMIT가 성능에 크게 기여한다.

#### 2글자 이하 키워드의 한계

3-gram은 3글자가 있어야 분해된다. "bo" (2글자) → 3-gram 없음 → Seq Scan fallback.
재즈 앨범명/아티스트명은 대부분 3글자 이상이라 실용적 문제 없음.

- 파일: `backendJava/migrations/015_add_trgm_index_to_mb_album.sql`
- 참고: `docs/개선/album-search-optimization.md`

---

### Full-Text Search (tsvector) — 왜 제외했는가

PostgreSQL에는 FTS(Full-Text Search)라는 내장 검색 기능도 있다.
텍스트를 **단어 단위**로 분해하고 **어근(stem)** 으로 정규화한다.

```
"Miles Davis plays" → tsvector: 'davis' 'mile' 'play'
```

**stemming**: "plays" → "play", "Miles" → "mile" 로 변환.
같은 어근의 단어들을 동일하게 취급하기 위해 사용한다.
("run", "running", "runs" → 모두 "run"으로 검색 가능)

**이 프로젝트에서 제외한 이유**:
고유명사(아티스트명, 앨범명)는 어근 변환이 오히려 왜곡이다.
- "Miles" → "mile" (단위 '마일'과 혼동)
- "Kind of Blue" → "kind" "blue" (단어 분리, 구문 검색 불가)

pg_trgm은 어근 변환 없이 문자 그대로 매칭하므로 고유명사 검색에 더 적합하다.

---

### Bloom Filter — 왜 이 케이스에 맞지 않는가

확률적 자료구조. "이 값이 집합에 **없다**는 걸 빠르게 판단"한다.

```
질문: "blue"가 mb_album에 있는가?
Bloom: "없다" → 확실히 없음 (False Negative 없음)
Bloom: "있다" → 실제로 없을 수도 있음 (False Positive 가능)
```

**가능한 것**: equality 검색 (`WHERE name = 'Kind of Blue'`)
**불가능한 것**: 범위/패턴 검색 (`WHERE name LIKE '%blue%'`)

이유: Bloom Filter는 특정 값의 존재 여부만 판단한다.
"어떤 값들이 이 패턴에 매칭되는가"는 알 수 없다.

| 인덱스 타입 | `=` | `LIKE 'x%'` | `LIKE '%x%'` |
|------------|-----|-------------|--------------|
| B-Tree | O | O | X |
| Bloom Filter | O | X | X |
| pg_trgm GIN | O | O | O |

---

### 인덱스 종류 전체 정리 — MySQL vs PostgreSQL

#### MySQL

| 인덱스 타입 | 설명 | 주 용도 |
|------------|------|---------|
| **B-Tree** | 기본 인덱스. InnoDB의 모든 인덱스가 내부적으로 B+Tree | `=`, `LIKE 'x%'`, 범위, 정렬 |
| **FULLTEXT** | 단어 단위 역색인. `MATCH ... AGAINST` 문법 사용 | 긴 텍스트 본문 검색 |
| **HASH** | 정확한 값만 O(1) 검색. MEMORY 엔진에서만 지원 (InnoDB 미지원) | `=` 검색 전용 |
| **SPATIAL** | 지리 좌표(GIS) 데이터 전용. R-Tree 구조 | `ST_Contains`, 거리 계산 |

> MySQL InnoDB는 사실상 B-Tree와 FULLTEXT만 실무에서 쓰인다.
> HASH는 InnoDB에서 내부적으로 Adaptive Hash Index로만 자동 사용 (직접 생성 불가).

#### PostgreSQL

| 인덱스 타입 | 설명 | 주 용도 |
|------------|------|---------|
| **B-Tree** | 기본 인덱스. `CREATE INDEX` 시 자동 선택 | `=`, `LIKE 'x%'`, 범위, 정렬 |
| **GIN** | Generalized Inverted Index. 한 행에서 여러 토큰 추출 | 배열, jsonb, tsvector, pg_trgm |
| **GiST** | Generalized Search Tree. 범위/근접 검색용 트리 | 지리 데이터, 범위 타입, 근접 검색 |
| **SP-GiST** | Space-Partitioned GiST. 불균형 데이터에 강함 | IP 주소, 좌표, 전화번호 |
| **BRIN** | Block Range Index. 블록 단위 최소/최대값만 저장 | 시계열/로그처럼 물리적 순서와 값 순서가 일치하는 대용량 테이블 |
| **Hash** | 정확한 값만 O(1) 검색 | `=` 검색 전용 (B-Tree보다 빠르지 않아 거의 안 씀) |
| **Bloom** | 확률적 자료구조. 여러 컬럼 동시 equality 필터링 | 다중 컬럼 `=` 조건, False Positive 허용 가능한 경우 |

#### 이 프로젝트에서 쓴 것

| 타입 | 어디서 | 왜 |
|------|--------|-----|
| B-Tree | 기존 `idx_mb_album_name` | 기본 인덱스 (LIKE '%x%'엔 소용없었음) |
| **GIN (pg_trgm)** | `idx_mb_album_name_trgm`, `idx_mb_album_artist_name_trgm` | `LOWER() LIKE '%x%'` 패턴 지원 |

#### 한 줄 요약

```
B-Tree   → 대부분의 일반 검색 (기본값)
GIN      → 배열/JSON/텍스트에서 여러 값을 뽑아 역색인이 필요할 때
GiST     → 지리/범위처럼 "겹치는가", "포함하는가" 검색
BRIN     → 시계열 로그처럼 수억 건인데 물리 순서와 값 순서가 일치할 때
Hash     → 이론상 빠르지만 실무에서 B-Tree로 대체됨
Bloom    → 다중 컬럼 equality 필터, 오탐 허용 가능한 특수 케이스
```

---

### 왜 GIN을 선택했는가 — 7종 전체 검토

`LOWER() LIKE '%x%'` 패턴을 지원하는지 기준으로 7종을 전부 검토했을 때:

| 타입 | `LIKE '%x%'` 지원 | 결론 |
|------|:-----------------:|------|
| B-Tree | X | 제외 |
| **GIN** | **O** | **채택** |
| **GiST** | **O** | 제외 (GIN과 비교 후) |
| SP-GiST | X | 제외 |
| BRIN | X | 제외 |
| Hash | X | 제외 |
| Bloom | X | 제외 |

#### 각 타입 제외 이유 상세

**B-Tree — 제외**
정렬된 트리 구조라 검색 시작점을 특정할 수 있어야 인덱스를 탄다.
`LIKE 'Blue%'`는 "Blue"로 시작하는 위치를 트리에서 찾아 거기서부터 읽으면 된다.
`LIKE '%blue%'`는 "blue"가 문자열 어디에 올지 모르므로 시작점을 특정할 수 없다 → 전체 스캔.
이미 `idx_mb_album_name` (B-Tree)이 있었지만 `EXPLAIN ANALYZE`에서 Seq Scan 478ms 확인.

**SP-GiST — 제외**
GiST의 변형이지만 다른 용도다. 공간을 불균등하게 분할하는 트리 구조로,
IP 주소(`192.168.x.x`), 전화번호, 좌표처럼 **값이 계층적으로 분해되는** 데이터에 강하다.
텍스트 substring 검색 연산자(`LIKE`)를 지원하지 않는다.

**BRIN — 제외**
Block Range Index. 블록 범위별로 최솟값/최댓값만 저장하는 매우 작은 인덱스다.

```
Block  1~100:   name 범위 "A Love..." ~ "All..."
Block 101~200:  name 범위 "Blue..." ~ "Bop..."
...
```

`WHERE name = 'Blue Train'`이면 해당 범위 블록만 읽는다.
단, 이게 동작하려면 **물리적 저장 순서와 값 순서가 일치**해야 한다.
`mb_album`은 MusicBrainz에서 랜덤 순서로 삽입되므로 범위 의미가 없다.
로그/시계열 테이블(created_at 순서 삽입)에만 효과적.

**Hash — 제외**
입력값을 해시 함수로 변환해 버킷에 저장한다. `=` equality는 O(1)이지만
해시는 "이 값이 정확히 있는가"만 답할 수 있다.
`LIKE '%blue%'`는 "blue를 포함하는 모든 값"이라 해시로 표현 자체가 불가능하다.

**Bloom — 제외**
여러 컬럼에 동시에 `=` 조건을 걸 때 불필요한 블록 읽기를 줄이는 용도다.
```sql
WHERE name = 'Kind of Blue' AND artist_name = 'Miles Davis'  -- Bloom 유효
WHERE name LIKE '%blue%'                                       -- Bloom 무효
```
`LIKE '%x%'` 패턴 자체를 처리할 수 없다.

실질적 후보는 **GIN과 GiST** 두 개였다. 둘 다 pg_trgm과 조합하면 `LIKE '%x%'`를 지원한다.

#### GIN vs GiST (pg_trgm 조합 시)

| 항목 | GIN | GiST |
|------|-----|------|
| 검색 속도 | 빠름 | GIN보다 느림 |
| 인덱스 크기 | 큼 (~20~40MB) | 작음 |
| 인덱스 빌드 속도 | 느림 | 빠름 |
| 쓰기 속도 (INSERT/UPDATE) | 느림 | GIN보다 빠름 |
| `similarity()` 퍼지 검색 | X | O |

**GIN 선택 근거**:
- 검색이 쓰기보다 훨씬 자주 발생 (입력마다 API 호출)
- 오타 허용을 제외했으므로 GiST만 지원하는 `similarity()` 불필요
- 인덱스 크기 20~40MB는 Supabase 허용 범위

**GiST가 유리한 경우**:
- 오타 허용 퍼지 검색이 필요할 때 (`similarity() > 0.3`)
- 쓰기가 매우 빈번한 테이블 (이 프로젝트는 MusicBrainz 주기적 배치 업데이트라 해당 없음)
