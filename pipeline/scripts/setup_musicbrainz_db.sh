#!/usr/bin/env bash
# =============================================================================
# setup_musicbrainz_db.sh
# MusicBrainz 로컬 PostgreSQL 최초 세팅 스크립트
#
# 목적:
#   build_album_reference.py 실행에 필요한 MusicBrainz 로컬 DB를 구축한다.
#   Supabase의 album_reference 3만 건에 mb_release_id 등을 매칭하기 위해
#   MusicBrainz 전체 덤프를 로컬 PostgreSQL에 적재한다.
#
#   배경 지식: pipeline/scripts/MUSICBRAINZ_SETUP_NOTES.md
#
# 사전 조건:
#   1. Docker Desktop 실행 중
#   2. musicbrainz-server repo의 admin/sql 디렉토리가 필요하다
#      (테이블 생성 DDL이 여기 있음 — 코드는 아니고 SQL 파일만 받는다)
#
#      git clone --depth=1 --filter=blob:none --sparse \
#        https://github.com/metabrainz/musicbrainz-server
#      cd musicbrainz-server && git sparse-checkout set admin/sql
#      cd ..   # JazzmateShop 루트로 돌아오기
#
# 실행 (JazzmateShop 루트에서):
#   bash pipeline/scripts/setup_musicbrainz_db.sh
#
# 갱신 시 (덤프 재다운로드 + 전체 재적재):
#   DUMP_DATE 변수를 최신 날짜로 바꾼 뒤:
#   bash pipeline/scripts/setup_musicbrainz_db.sh --reload
# =============================================================================

# 오류 발생 시 즉시 중단, 미정의 변수 사용 금지, 파이프 오류도 감지
set -euo pipefail

# ---------------------------------------------------------------------------
# 설정값 — 변경이 필요하면 여기만 수정
# ---------------------------------------------------------------------------

CONTAINER_NAME="musicbrainz-db"
PG_PORT=5433          # 로컬 5432와 충돌 방지용으로 5433 사용
PG_USER=postgres
PG_PASS=postgres
PG_DB=musicbrainz_db
DATA_DIR="$HOME/musicbrainz-data"   # PostgreSQL 데이터 파일 저장 위치 (컨테이너 재시작해도 유지)
DUMP_DIR="$HOME/mb-dump"            # 덤프 파일 다운로드 위치

# 갱신 시 아래 날짜를 최신으로 변경
# 최신 날짜 확인: https://data.metabrainz.org/pub/musicbrainz/data/fullexport/
DUMP_DATE="20260613-002047"

# ---------------------------------------------------------------------------
# 경로 계산 — 어느 디렉토리에서 실행해도 동작하도록 절대경로 사용
# ---------------------------------------------------------------------------

# 이 스크립트가 있는 디렉토리 (pipeline/scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# JazzmateShop 루트 (pipeline/scripts/의 두 단계 위)
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# musicbrainz-server DDL 파일 위치
SQL_DIR="$REPO_DIR/musicbrainz-server/admin/sql"

# --reload 플래그 확인
RELOAD=false
if [[ "${1:-}" == "--reload" ]]; then
  RELOAD=true
  echo ">>> RELOAD 모드: 기존 스키마를 삭제하고 처음부터 다시 세팅합니다"
fi

# ---------------------------------------------------------------------------
# 단계 1. Docker PostgreSQL 컨테이너 실행
#
# MusicBrainz 전용 PostgreSQL 16 컨테이너를 띄운다.
# - 포트 5433으로 외부에서 접근 가능
# - ~/musicbrainz-data에 데이터를 영구 저장 (컨테이너 삭제해도 데이터 유지)
# - 컨테이너가 이미 있으면 재생성하지 않고 시작만 한다
# ---------------------------------------------------------------------------

echo ""
echo "[1/6] Docker PostgreSQL 컨테이너 실행"

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "  컨테이너 이미 존재 → 시작"
  docker start "$CONTAINER_NAME"
else
  echo "  컨테이너 신규 생성"
  docker run -d \
    --name "$CONTAINER_NAME" \
    -e POSTGRES_PASSWORD="$PG_PASS" \
    -e POSTGRES_DB="$PG_DB" \
    -p "${PG_PORT}:5432" \
    -v "${DATA_DIR}:/var/lib/postgresql/data" \
    postgres:16
fi

# PostgreSQL이 완전히 뜰 때까지 대기 (컨테이너는 떴어도 DB 프로세스가 준비되는 데 수 초 걸림)
echo "  PostgreSQL 준비 대기 중..."
until PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB -c "SELECT 1" &>/dev/null; do
  sleep 1
done
echo "  준비 완료"

# ---------------------------------------------------------------------------
# 단계 2. 스키마 초기화 및 생성
#
# MusicBrainz는 'public' 스키마 대신 'musicbrainz'라는 별도 스키마를 사용한다.
# search_path 설정으로 테이블 접근 시 스키마 prefix(musicbrainz.)를 생략할 수 있다.
#
# ICU collation: 문자열 정렬 규칙. MusicBrainz 전용 규칙으로,
# 이게 없으면 CreateTables.sql 실행 시 오류가 난다.
# 자세한 설명: MUSICBRAINZ_SETUP_NOTES.md
# ---------------------------------------------------------------------------

echo ""
echo "[2/6] 스키마 초기화 및 생성"

if $RELOAD; then
  echo "  기존 musicbrainz 스키마 삭제 (CASCADE = 하위 테이블/타입 모두 삭제)"
  PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
    -c "DROP SCHEMA IF EXISTS musicbrainz CASCADE; DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
fi

PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB <<SQL
-- musicbrainz 전용 스키마 생성
CREATE SCHEMA IF NOT EXISTS musicbrainz;

-- 이 DB에 접속하면 자동으로 musicbrainz 스키마를 먼저 탐색
ALTER DATABASE $PG_DB SET search_path TO musicbrainz, public;

-- MusicBrainz 전용 문자열 정렬 규칙 등록 (테이블 생성에 필요)
CREATE COLLATION IF NOT EXISTS musicbrainz.musicbrainz
  (provider = icu, locale = 'und-u-kf-lower-kn-true', deterministic = false);
SQL

echo "  완료"

# ---------------------------------------------------------------------------
# 단계 3. DDL 적용 (테이블 구조 생성)
#
# musicbrainz-server 공식 repo의 SQL 파일로 테이블 구조를 만든다.
# 순서가 중요하다: Extensions → Types → Tables → PrimaryKeys
#
# - Extensions.sql : cube, unaccent 등 PostgreSQL 확장 기능 설치
# - CreateTypes.sql : ENUM 타입 정의 (테이블보다 먼저 있어야 함)
# - CreateTables.sql: 실제 테이블 생성
# - CreatePrimaryKeys.sql: 기본키 설정
#
# 순서를 바꾸면 "type does not exist" 같은 오류가 발생한다.
# ---------------------------------------------------------------------------

echo ""
echo "[3/6] DDL 적용 (테이블 구조 생성)"

echo "  Extensions 적용 (cube, unaccent 등)"
PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
  -f "${SQL_DIR}/Extensions.sql"

echo "  Types 적용 (ENUM 타입)"
PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
  -f "${SQL_DIR}/CreateTypes.sql"

echo "  Tables 적용"
PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
  -f "${SQL_DIR}/CreateTables.sql"

echo "  Primary Keys 적용"
PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
  -f "${SQL_DIR}/CreatePrimaryKeys.sql"

echo "  완료"

# ---------------------------------------------------------------------------
# 단계 4. 덤프 파일 다운로드
#
# MusicBrainz는 전체 DB를 탭 구분 텍스트(TSV) 형식으로 배포한다.
# pg_dump/pg_restore 형식이 아니므로 다운로드 후 COPY로 직접 적재해야 한다.
#
# 필요한 파일 2개:
#   mbdump.tar.bz2         (~6.8GB): artist, release, release_group, label 등
#   mbdump-derived.tar.bz2 (~477MB): tag, release_group_tag (재즈 필터링에 필수)
#
# 덤프가 이미 있으면 스킵한다. --reload 시 재다운로드.
# ---------------------------------------------------------------------------

BASE_URL="https://data.metabrainz.org/pub/musicbrainz/data/fullexport/${DUMP_DATE}"

if $RELOAD || [ ! -d "$DUMP_DIR/mbdump" ]; then
  echo ""
  echo "[4/6] 덤프 파일 다운로드 (총 ~7.3GB, 시간 걸림)"
  mkdir -p "$DUMP_DIR"
  cd "$DUMP_DIR"

  echo "  mbdump.tar.bz2 다운로드 중..."
  curl -L -o mbdump.tar.bz2 "$BASE_URL/mbdump.tar.bz2" --progress-bar

  echo "  mbdump-derived.tar.bz2 다운로드 중..."
  curl -L -o mbdump-derived.tar.bz2 "$BASE_URL/mbdump-derived.tar.bz2" --progress-bar

  echo "  압축 해제 중 (bz2 → TSV 텍스트 파일, 20~40분 소요)"
  tar xjf mbdump.tar.bz2
  tar xjf mbdump-derived.tar.bz2
  cd -
  echo "  완료"
else
  echo ""
  echo "[4/6] 덤프 이미 존재 → 스킵 (재다운로드 하려면 --reload 옵션 사용)"
fi

# ---------------------------------------------------------------------------
# 단계 5. 데이터 적재 (COPY)
#
# 압축 해제된 TSV 파일을 PostgreSQL COPY 명령으로 테이블에 밀어넣는다.
# COPY는 INSERT보다 수십 배 빠른 대용량 적재 방법이다.
#
# 적재 순서: FK(외래키) 참조 관계 때문에 순서가 있다.
#   artist → artist_credit → artist_credit_name
#   release_group → release → release_label, release_country
#   label, tag → release_group_tag
#
# FORMAT text : TSV 형식
# NULL '\N'   : MusicBrainz 덤프에서 NULL을 \N으로 표시하므로 이를 NULL로 변환
# ---------------------------------------------------------------------------

echo ""
echo "[5/6] 데이터 적재 (COPY)"

# 적재할 테이블 목록 (순서 중요 — FK 의존성 순)
tables=(
  artist
  artist_credit
  artist_credit_name
  release_group
  release_group_meta
  release
  release_label
  release_country
  label
  tag
  release_group_tag
)

for table in "${tables[@]}"; do
  file="$DUMP_DIR/mbdump/$table"
  if [ -f "$file" ]; then
    echo "  COPY $table..."
    PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
      -c "\COPY musicbrainz.$table FROM '$file' WITH (FORMAT text, NULL '\N')"
  else
    echo "  [경고] $file 없음 → 스킵"
  fi
done

echo "  완료"

# ---------------------------------------------------------------------------
# 단계 6. 인덱스 생성
#
# 데이터 적재 후 인덱스를 만드는 게 효율적이다.
# (빈 테이블에 인덱스를 먼저 만들면 INSERT마다 인덱스를 갱신해서 느림)
#
# build_album_reference.py의 매칭 쿼리가 artist.name, release.name 등으로
# 조인하므로 인덱스가 없으면 수 시간이 걸릴 수 있다.
# ---------------------------------------------------------------------------

echo ""
echo "[6/6] 인덱스 생성 (데이터 양에 따라 수십 분 소요)"
PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \
  -f "${SQL_DIR}/CreateIndexes.sql" || echo "  [경고] 일부 인덱스 실패 (무시하고 계속)"

# ---------------------------------------------------------------------------
# 완료
# ---------------------------------------------------------------------------

echo ""
echo "=============================================="
echo "  세팅 완료"
echo "=============================================="
echo ""
echo "  환경변수 설정:"
echo "  export MB_DB_URL=postgresql://${PG_USER}:${PG_PASS}@localhost:${PG_PORT}/${PG_DB}"
echo ""
echo "  적재 확인:"
echo "  PGPASSWORD=$PG_PASS psql -h localhost -p $PG_PORT -U $PG_USER -d $PG_DB \\"
echo "    -c 'SELECT count(*) FROM musicbrainz.artist;'"
echo ""
echo "  다음 단계:"
echo "  python pipeline/scripts/build_album_reference.py --dry-run --limit 50"
