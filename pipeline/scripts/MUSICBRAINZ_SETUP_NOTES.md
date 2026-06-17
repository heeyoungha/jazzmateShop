# MusicBrainz DB 세팅 개념 노트

이 문서는 `setup_musicbrainz_db.sh`와 `load_mb_dump.sh`를 이해하기 위한 배경 지식을 정리한다.

---

## 왜 MusicBrainz DB가 필요한가?

`build_album_reference.py` 스크립트는 Supabase의 `album_reference` 테이블(재즈 앨범 ~3만 건)에
MusicBrainz의 공식 앨범 ID(`mb_release_id`, `mb_artist_id` 등)를 매칭해서 채워넣는다.

MusicBrainz는 세계 최대 오픈 음악 메타데이터 DB로, 앨범/아티스트에 고유 UUID를 부여한다.
이 UUID를 확보해두면 나중에 앨범 커버, 발매 정보 등을 API로 조회할 수 있다.

---

## MusicBrainz 덤프란?

MusicBrainz는 전체 DB를 주 2회 공개 배포한다 (풀 스냅샷).
배포 형식은 PostgreSQL dump가 아니라 **탭 구분 텍스트 파일(TSV)** 이다.

```
mbdump/artist 파일 예시:
352	\N	Miles Davis	\N	1926	9	26	1991	9	28	...
```

- 각 줄 = DB 테이블의 행 1개
- 컬럼은 탭(`\t`)으로 구분
- NULL은 `\N` 으로 표시

따라서 파일을 받은 뒤 PostgreSQL에 `COPY` 명령으로 직접 밀어넣어야 한다.
`pg_restore`가 아닌 `COPY`를 쓰는 이유가 이것이다.

다운로드 경로: https://data.metabrainz.org/pub/musicbrainz/data/fullexport/

---

## 우리가 받는 파일 2개

| 파일 | 크기 | 포함 테이블 |
|---|---|---|
| `mbdump.tar.bz2` | ~6.8GB | artist, artist_credit, release, release_group, label 등 |
| `mbdump-derived.tar.bz2` | ~477MB | tag, release_group_tag (재즈 필터링에 필수) |

전체 덤프 중 우리에게 필요한 테이블만 골라서 적재한다.
나머지(edit 이력, 사용자 데이터 등)는 적재하지 않는다.

---

## PostgreSQL 스키마 구조

MusicBrainz는 `public` 스키마 대신 `musicbrainz`라는 별도 스키마를 사용한다.

```
musicbrainz_db (데이터베이스)
└── musicbrainz (스키마)
    ├── artist
    ├── release
    ├── release_group
    ├── tag
    └── ...
```

`search_path`를 `musicbrainz, public`으로 설정하면
`SELECT * FROM artist` 처럼 스키마 prefix 없이 쿼리할 수 있다.

---

## DDL 적용 순서가 중요한 이유

PostgreSQL은 참조하는 대상이 먼저 존재해야 한다.

```
Extensions (cube, unaccent 등 확장 기능)
    ↓
Types (ENUM 타입 정의 — CreateTypes.sql)
    ↓
Tables (테이블 생성 — CreateTables.sql)
    ↓
Primary Keys (기본키 — CreatePrimaryKeys.sql)
    ↓
데이터 COPY 적재
    ↓
Indexes (인덱스 — CreateIndexes.sql, 데이터 있어야 효율적)
```

순서를 바꾸면 "type does not exist", "relation does not exist" 같은 오류가 난다.
(실제로 세팅 중 이 오류들을 만났다.)

---

## ICU Collation이란?

`CREATE COLLATION musicbrainz (provider = icu, locale = 'und-u-kf-lower-kn-true')`

Collation = 문자열 정렬/비교 규칙이다.
MusicBrainz가 쓰는 ICU collation의 의미:
- `und` : 언어 무관 (universal)
- `kf-lower` : 소문자를 먼저 정렬
- `kn-true` : 숫자를 자연수 순서로 정렬 ("9" < "10")

이게 없으면 `CreateTables.sql` 실행 시 오류가 난다.

---

## 포트를 5433으로 쓰는 이유

로컬에 PostgreSQL이 이미 설치되어 있으면 기본 포트 5432를 쓰고 있을 수 있다.
충돌을 피하기 위해 MusicBrainz 전용 컨테이너는 5433을 사용한다.

---

## 갱신 주기

MusicBrainz는 주 2회 스냅샷을 배포하지만,
재즈 앨범 데이터는 대부분 수십 년 된 클래식이라 변경이 거의 없다.

갱신이 필요한 경우 (새 앨범 대량 추가, 매칭 품질 개선 등):
```bash
bash pipeline/scripts/setup_musicbrainz_db.sh --reload
```
`DUMP_DATE` 변수를 최신 날짜로 바꾼 뒤 실행하면 전체 재적재된다.
