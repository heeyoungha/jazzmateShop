#!/usr/bin/env bash
# =============================================================================
# load_mb_dump.sh
# MusicBrainz 덤프 데이터 적재 스크립트 (단독 실행용)
#
# 목적:
#   setup_musicbrainz_db.sh로 테이블 구조는 만들었지만
#   데이터 적재만 다시 하고 싶을 때 단독으로 실행한다.
#   (예: COPY 도중 오류로 중단된 경우, 또는 데이터만 갱신할 때)
#
#   배경 지식: pipeline/scripts/MUSICBRAINZ_SETUP_NOTES.md
#
# 사전 조건:
#   - musicbrainz-db 컨테이너가 실행 중이어야 한다
#   - ~/mb-dump/mbdump/ 디렉토리에 TSV 파일이 압축 해제되어 있어야 한다
#
# 실행:
#   bash pipeline/scripts/load_mb_dump.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 설정값
# ---------------------------------------------------------------------------

export PGPASSWORD=postgres
PG="psql -h localhost -p 5433 -U postgres -d musicbrainz_db"

# 압축 해제된 TSV 파일 위치
DUMP="$HOME/mb-dump/mbdump"

# ---------------------------------------------------------------------------
# 데이터 적재 (COPY)
#
# MusicBrainz 덤프는 탭 구분 텍스트(TSV) 파일이다.
# PostgreSQL의 COPY 명령으로 파일을 테이블에 직접 밀어넣는다.
# INSERT보다 수십 배 빠르다.
#
# 적재 순서: 외래키(FK) 의존 관계 때문에 순서가 있다.
#   부모 테이블을 자식보다 먼저 적재해야 한다.
#
# FORMAT text : TSV(탭 구분) 형식
# NULL '\N'   : 덤프에서 NULL을 \N으로 표시하므로 이를 NULL로 변환
# ---------------------------------------------------------------------------

tables=(
  artist              # 아티스트 기본 정보
  artist_credit       # 앨범에 표시되는 아티스트 크레딧 (여러 아티스트 공동 작업 포함)
  artist_credit_name  # 크레딧과 실제 아티스트 연결 테이블
  release_group       # 앨범 그룹 (동일 앨범의 여러 버전을 묶음)
  release             # 실제 발매본 (국가/날짜별로 다를 수 있음)
  release_label       # 발매 레이블 정보
  release_country     # 발매 국가 정보
  label               # 레이블 상세 정보
  tag                 # 태그 목록 (jazz, blues 등 장르 태그)
  release_group_tag   # 앨범 그룹과 태그 연결 (재즈 필터링에 핵심)
)

echo "데이터 적재 시작..."
echo ""

for table in "${tables[@]}"; do
  file="$DUMP/$table"
  if [ -f "$file" ]; then
    echo "COPY $table..."
    $PG -c "\COPY musicbrainz.$table FROM '$file' WITH (FORMAT text, NULL '\N')"
    echo "  완료"
  else
    echo "  [경고] $file 없음 → 스킵"
    echo "  (mbdump.tar.bz2 또는 mbdump-derived.tar.bz2 압축 해제 필요)"
  fi
done

# ---------------------------------------------------------------------------
# 완료
# ---------------------------------------------------------------------------

echo ""
echo "=============================================="
echo "  적재 완료"
echo "=============================================="
echo ""
echo "  적재 확인:"
echo "  PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d musicbrainz_db \\"
echo "    -c 'SELECT count(*) FROM musicbrainz.artist;'"
echo ""
echo "  다음 단계:"
echo "  python pipeline/scripts/build_album_reference.py --dry-run --limit 50"
