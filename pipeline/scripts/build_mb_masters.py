"""
build_mb_masters.py
-------------------
MusicBrainz 로컬 PostgreSQL 덤프에서 재즈 아티스트/앨범을 조회하여
Supabase의 mb_artist, mb_album 테이블을 채운다.

사전 조건:
  1. MusicBrainz 전체 덤프가 로컬 PostgreSQL에 복원되어 있어야 한다.
  2. Supabase에 008_create_mb_master_tables.sql 마이그레이션이 실행되어 있어야 한다.
  3. 환경변수 설정 (.env 또는 shell):
       MB_DB_URL       = postgresql://user:pass@localhost:5432/musicbrainz
       SUPABASE_DB_URL = postgresql://...  (Supabase Direct Connection URL)

실행:
  python pipeline/scripts/build_mb_masters.py
  python pipeline/scripts/build_mb_masters.py --dry-run   # 건수만 출력, DB 저장 안 함
  python pipeline/scripts/build_mb_masters.py --limit 1000
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

MB_DB_URL       = os.environ["MB_DB_URL"]
SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

BATCH_SIZE = 1000  # Supabase upsert 배치 크기


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class MbArtistRow:
    gid:        str
    name:       str
    sort_name:  str
    begin_year: int | None
    area:       str | None


@dataclass
class MbAlbumRow:
    gid:               str
    name:              str
    artist_id:         str | None
    first_release_year: int | None
    cover_art_url:     str | None
    genres:            list[str] | None


# ---------------------------------------------------------------------------
# MusicBrainz 쿼리
# ---------------------------------------------------------------------------

# 재즈 및 하위 장르 태그 목록
JAZZ_TAGS = [
    'jazz', 'contemporary jazz', 'free jazz', 'jazz-funk', 'jazz rock',
    'soul jazz', 'smooth jazz', 'latin jazz', 'avant-garde jazz', 'cool jazz',
    'jazz fusion', 'future jazz', 'acid jazz', 'vocal jazz', 'nu jazz',
    'gypsy jazz', 'afro-cuban jazz', 'jazz pop', 'dark jazz', 'instrumental jazz',
    'jazz-rock', 'soul-jazz', 'spiritual jazz', 'crossover jazz', 'bebop',
    'hard bop', 'post-bop', 'modal jazz', 'swing', 'bossa nova', 'fusion',
]

# 재즈 태그가 달린 release_group의 아티스트만 추출
MB_ARTIST_QUERY = """
SELECT DISTINCT
    a.gid                   AS gid,
    a.name                  AS name,
    a.sort_name             AS sort_name,
    a.begin_date_year       AS begin_year,
    ar.name                 AS area
FROM artist a
JOIN artist_credit_name acn ON acn.artist = a.id
JOIN artist_credit ac       ON ac.id = acn.artist_credit
JOIN release_group rg       ON rg.artist_credit = ac.id
JOIN release_group_tag rgt  ON rgt.release_group = rg.id
JOIN tag t                  ON t.id = rgt.tag AND lower(t.name) = ANY(%s)
LEFT JOIN area ar           ON ar.id = a.area
ORDER BY a.name;
"""

# 재즈 태그가 달린 release_group만 추출 (genres 제외 — 별도 쿼리로 조회)
# DISTINCT ON (rg.id): 동일 앨범에 jazz 관련 태그가 여러 개 달려도 1건만 추출
# position 조건 제거: acn.position = 1 조건이 앨범 자체를 필터링하는 부작용이 있었음
#   → DISTINCT ON (rg.id)로 대표 아티스트 1명만 취하되 앨범 누락 없음
MB_ALBUM_QUERY = """
SELECT DISTINCT ON (rg.id)
    rg.gid                          AS gid,
    rg.name                         AS name,
    a.gid                           AS artist_id,
    rgm.first_release_date_year     AS first_release_year
FROM release_group rg
JOIN release_group_tag rgt  ON rgt.release_group = rg.id
JOIN tag t                  ON t.id = rgt.tag AND lower(t.name) = ANY(%s)
JOIN artist_credit ac       ON ac.id = rg.artist_credit
JOIN artist_credit_name acn ON acn.artist_credit = ac.id
JOIN artist a               ON a.id = acn.artist
LEFT JOIN release_group_meta rgm ON rgm.id = rg.id
ORDER BY rg.id;
"""

# release_group gid 목록으로 태그 일괄 조회
MB_GENRES_QUERY = """
SELECT
    rg.gid      AS gid,
    t.name      AS tag_name,
    rgt.count   AS tag_count
FROM release_group rg
JOIN release_group_tag rgt ON rgt.release_group = rg.id
JOIN tag t                 ON t.id = rgt.tag
WHERE rg.gid = ANY(%s::uuid[])
ORDER BY rg.gid, rgt.count DESC;
"""


# ---------------------------------------------------------------------------
# 데이터 로드
# ---------------------------------------------------------------------------

def fetch_mb_artists(mb_conn, limit: int | None) -> list[MbArtistRow]:
    log.info("MusicBrainz 재즈 아티스트 조회 중...")
    sql = MB_ARTIST_QUERY
    if limit:
        sql = sql.replace("ORDER BY a.name;", f"ORDER BY a.name LIMIT {limit};")

    cur = mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql, (JAZZ_TAGS,))
    rows = cur.fetchall()
    log.info("  아티스트 %d건 로드 완료", len(rows))
    return [
        MbArtistRow(
            gid=str(row["gid"]),
            name=row["name"],
            sort_name=row["sort_name"],
            begin_year=row["begin_year"],
            area=row["area"],
        )
        for row in rows
    ]


def fetch_mb_albums(mb_conn, limit: int | None) -> list[MbAlbumRow]:
    log.info("MusicBrainz 재즈 앨범 조회 중...")
    sql = MB_ALBUM_QUERY
    if limit:
        sql = sql.replace(
            "ORDER BY rg.id;",
            f"ORDER BY rg.id LIMIT {limit};"
        )

    cur = mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql, (JAZZ_TAGS,))
    rows = cur.fetchall()
    log.info("  앨범 %d건 로드 완료", len(rows))

    # gid 목록으로 태그 일괄 조회 (서브쿼리 대신 별도 쿼리로 성능 개선)
    gids = [str(row["gid"]) for row in rows]
    genres_map: dict[str, list[str]] = {}
    if gids:
        log.info("  장르 태그 조회 중...")
        cur.execute(MB_GENRES_QUERY, (gids,))
        for tag_row in cur.fetchall():
            gid = str(tag_row["gid"])
            genres_map.setdefault(gid, []).append(tag_row["tag_name"])
        log.info("  장르 태그 로드 완료")

    return [
        MbAlbumRow(
            gid=str(row["gid"]),
            name=row["name"],
            artist_id=str(row["artist_id"]) if row["artist_id"] else None,
            first_release_year=row["first_release_year"],
            cover_art_url=f"https://coverartarchive.org/release-group/{row['gid']}/front",
            genres=genres_map.get(str(row["gid"]), []),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_artists(sb_conn, artists: list[MbArtistRow]) -> None:
    sql = """
        INSERT INTO mb_artist (gid, name, sort_name, begin_year, area)
        VALUES %s
        ON CONFLICT (gid) DO UPDATE SET
            name       = EXCLUDED.name,
            sort_name  = EXCLUDED.sort_name,
            begin_year = EXCLUDED.begin_year,
            area       = EXCLUDED.area,
            updated_at = NOW()
    """
    cur = sb_conn.cursor()
    values = [(a.gid, a.name, a.sort_name, a.begin_year, a.area) for a in artists]
    psycopg2.extras.execute_values(cur, sql, values, page_size=BATCH_SIZE)
    log.info("  mb_artist upsert: %d건", len(artists))


def upsert_albums(sb_conn, albums: list[MbAlbumRow]) -> None:
    sql = """
        INSERT INTO mb_album (gid, name, artist_id, first_release_year, cover_art_url, genres)
        VALUES %s
        ON CONFLICT (gid) DO UPDATE SET
            name               = EXCLUDED.name,
            artist_id          = EXCLUDED.artist_id,
            first_release_year = EXCLUDED.first_release_year,
            cover_art_url      = EXCLUDED.cover_art_url,
            genres             = EXCLUDED.genres,
            updated_at         = NOW()
    """
    cur = sb_conn.cursor()
    values = [
        (al.gid, al.name, al.artist_id, al.first_release_year, al.cover_art_url, al.genres)
        for al in albums
    ]
    psycopg2.extras.execute_values(cur, sql, values, page_size=BATCH_SIZE)
    log.info("  mb_album upsert: %d건", len(albums))


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def run(dry_run: bool, limit: int | None) -> None:
    log.info("=== build_mb_masters 시작 (dry_run=%s, limit=%s) ===", dry_run, limit)

    mb_conn = psycopg2.connect(
        MB_DB_URL,
        options="-c max_parallel_workers_per_gather=0"  # Docker shared memory 부족 방지
    )
    mb_conn.set_session(readonly=True, autocommit=True)

    sb_conn = psycopg2.connect(SUPABASE_DB_URL)

    try:
        artists = fetch_mb_artists(mb_conn, limit)
        albums  = fetch_mb_albums(mb_conn, limit)

        if dry_run:
            log.info("[dry-run] mb_artist 저장 예정: %d건", len(artists))
            log.info("[dry-run] mb_album  저장 예정: %d건", len(albums))
            for al in albums[:5]:
                log.info("  샘플: %s / %s (%s)", al.name, al.artist_id, al.first_release_year)
            return

        # 아티스트 먼저 (mb_album.artist_id FK 때문에)
        upsert_artists(sb_conn, artists)
        upsert_albums(sb_conn, albums)

        sb_conn.commit()
        log.info("커밋 완료")
        log.info(
            "=== 완료 | mb_artist: %d건 / mb_album: %d건 ===",
            len(artists), len(albums),
        )

    except Exception:
        sb_conn.rollback()
        log.exception("오류 발생, 롤백")
        sys.exit(1)

    finally:
        mb_conn.close()
        sb_conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MusicBrainz → mb_artist / mb_album 마스터 테이블 구축")
    parser.add_argument("--dry-run", action="store_true", help="건수만 출력, DB 저장 안 함")
    parser.add_argument("--limit",   type=int, default=None, help="처리할 최대 건수 (기본: 전체)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(dry_run=args.dry_run, limit=args.limit)
