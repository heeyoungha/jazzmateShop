"""
build_album_reference.py
------------------------
MusicBrainz 로컬 PostgreSQL 덤프에서 재즈 앨범을 조회하여
Supabase의 album_reference 테이블에 mb_* 컬럼을 채운다.

사전 조건:
  1. MusicBrainz 전체 덤프가 로컬 PostgreSQL에 복원되어 있어야 한다.
     공식 덤프: https://data.metabrainz.org/pub/musicbrainz/data/fullexport/
     복원 방법: https://musicbrainz.org/doc/MusicBrainz_Database/Download
  2. 환경변수 설정 (.env 또는 shell):
       MB_DB_URL   = postgresql://user:pass@localhost:5432/musicbrainz
       SUPABASE_DB_URL = postgresql://...  (Supabase Direct Connection URL)

실행:
  python pipeline/scripts/build_album_reference.py
  python pipeline/scripts/build_album_reference.py --dry-run      # 매칭 결과만 출력, DB 저장 안 함
  python pipeline/scripts/build_album_reference.py --limit 100    # 100건만 처리
"""

import argparse
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

MB_DB_URL      = os.environ["MB_DB_URL"]
SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]

# 매칭 임계값: 이 점수 이상이어야 mb_matched = true
MATCH_THRESHOLD = 0.85

# 연도 불일치 허용 범위 (±N년): 같은 앨범이 여러 국가에서 다른 연도에 발매될 수 있음
YEAR_TOLERANCE = 2


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class AlbumRow:
    """Supabase album_reference 행"""
    id: str
    raw_id: str
    artist_name: str
    album_title: str
    release_year: str | None


@dataclass
class MbCandidate:
    """MusicBrainz 후보 행"""
    mb_release_id: str
    mb_artist_id: str
    mb_release_group_id: str
    release_name: str
    artist_name: str
    release_date: str | None
    country: str | None


# ---------------------------------------------------------------------------
# MusicBrainz 재즈 앨범 캐시 구축
# ---------------------------------------------------------------------------

JAZZ_CACHE_QUERY = """
WITH jazz_rg AS (
    -- 재즈 태그가 달린 release_group만 먼저 추려 JOIN 대상을 줄인다
    SELECT DISTINCT rgt.release_group
    FROM musicbrainz.release_group_tag rgt
    JOIN musicbrainz.tag t ON rgt.tag = t.id AND lower(t.name) = 'jazz'
),
release_date AS (
    -- release별 최초 발매 연도를 미리 집계 (correlated subquery 제거)
    SELECT release, MIN(date_year) AS date_year
    FROM musicbrainz.release_country
    WHERE date_year IS NOT NULL
    GROUP BY release
    UNION ALL
    SELECT release, MIN(date_year) AS date_year
    FROM musicbrainz.release_unknown_country
    WHERE date_year IS NOT NULL
    GROUP BY release
),
release_min_year AS (
    SELECT release, MIN(date_year) AS min_year
    FROM release_date
    GROUP BY release
),
best_release AS (
    -- release_group당 Official 우선, 없으면 다른 status도 허용
    -- 가장 오래된 발매본 1건만 선택
    SELECT DISTINCT ON (r.release_group)
        r.id, r.gid, r.release_group, r.artist_credit
    FROM musicbrainz.release r
    JOIN jazz_rg jrg ON jrg.release_group = r.release_group
    LEFT JOIN release_min_year rmy ON rmy.release = r.id
    ORDER BY r.release_group,
             CASE WHEN r.status = 1 THEN 0 ELSE 1 END,  -- Official 우선
             rmy.min_year NULLS LAST,
             r.id
)
SELECT
    br.gid                          AS mb_release_id,
    a.gid                           AS mb_artist_id,
    rg.gid                          AS mb_release_group_id,
    rg.name                         AS release_name,
    a.name                          AS artist_name,
    -- 발매일: release_country 우선, 없으면 release_unknown_country
    CASE
        WHEN COALESCE(rc.date_year, ruc.date_year) IS NULL THEN NULL
        WHEN COALESCE(rc.date_month, ruc.date_month) IS NOT NULL
             AND COALESCE(rc.date_day, ruc.date_day) IS NOT NULL
            THEN COALESCE(rc.date_year, ruc.date_year)::TEXT || '-'
                 || LPAD(COALESCE(rc.date_month, ruc.date_month)::TEXT, 2, '0') || '-'
                 || LPAD(COALESCE(rc.date_day, ruc.date_day)::TEXT, 2, '0')
        WHEN COALESCE(rc.date_month, ruc.date_month) IS NOT NULL
            THEN COALESCE(rc.date_year, ruc.date_year)::TEXT || '-'
                 || LPAD(COALESCE(rc.date_month, ruc.date_month)::TEXT, 2, '0')
        ELSE COALESCE(rc.date_year, ruc.date_year)::TEXT
    END                             AS release_date,
    ar.name                         AS country
FROM best_release br
JOIN musicbrainz.release_group rg   ON rg.id = br.release_group
JOIN musicbrainz.artist_credit ac   ON ac.id = br.artist_credit
JOIN musicbrainz.artist_credit_name acn ON acn.artist_credit = ac.id AND acn.position = 0
JOIN musicbrainz.artist a           ON a.id = acn.artist
LEFT JOIN musicbrainz.release_country rc        ON rc.release = br.id
LEFT JOIN musicbrainz.release_unknown_country ruc ON ruc.release = br.id
LEFT JOIN musicbrainz.area ar                   ON ar.id = rc.country
GROUP BY br.gid, a.gid, rg.gid, rg.name, a.name,
         rc.date_year, rc.date_month, rc.date_day,
         ruc.date_year, ruc.date_month, ruc.date_day,
         ar.name
ORDER BY a.name, rg.name;
"""


def build_mb_jazz_cache(mb_conn) -> tuple[dict[str, list[MbCandidate]], dict[str, list[str]]]:
    """
    MusicBrainz에서 재즈 앨범 전체를 읽어
    { normalized_artist_name: [MbCandidate, ...] } 딕셔너리로 반환.
    추가로 { prefix2: [artist_key, ...] } 인덱스도 반환해 fallback 탐색을 빠르게 한다.
    """
    log.info("MusicBrainz 재즈 앨범 캐시 구축 중...")
    cur = mb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(JAZZ_CACHE_QUERY)
    rows = cur.fetchall()
    log.info("  MusicBrainz 재즈 앨범 %d건 로드 완료", len(rows))

    cache: dict[str, list[MbCandidate]] = {}
    prefix_index: dict[str, list[str]] = {}  # 앞 2글자 → artist key 목록
    for row in rows:
        key = normalize(row["artist_name"])
        candidate = MbCandidate(
            mb_release_id=str(row["mb_release_id"]),
            mb_artist_id=str(row["mb_artist_id"]),
            mb_release_group_id=str(row["mb_release_group_id"]),
            release_name=row["release_name"],
            artist_name=row["artist_name"],
            release_date=row["release_date"],
            country=row["country"],
        )
        cache.setdefault(key, []).append(candidate)
        prefix = key[:2] if len(key) >= 2 else key
        if key not in prefix_index.get(prefix, []):
            prefix_index.setdefault(prefix, []).append(key)

    log.info("  고유 아티스트 %d명 인덱싱 완료", len(cache))
    return cache, prefix_index


# ---------------------------------------------------------------------------
# 매칭 로직
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """비교용 정규화: 소문자, 약어 확장, 특수문자 제거, 공백 정리"""
    text = text.lower()
    # 약어 정규화
    text = re.sub(r"\bvol\.?\s*(\d+|one|two|three|four|five)\b", lambda m: "volume " + m.group(1), text)
    text = re.sub(r"\bpt\.?\s*(\d+)\b", r"part \1", text)
    text = re.sub(r"\bno\.?\s*(\d+)\b", r"number \1", text)
    text = re.sub(r"\bst\.?\b", "saint", text)
    text = re.sub(r"[''\"()[\].,!?&\-:]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def string_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def year_penalty(atj_year: str | None, mb_date: str | None) -> float:
    """
    연도 불일치 시 페널티 반환 (0.0 = 패널티 없음, 1.0 = 완전 불일치).
    연도 정보가 없으면 페널티 없음.
    """
    if not atj_year or not mb_date:
        return 0.0
    try:
        y1 = int(atj_year)
        y2 = int(mb_date[:4])
        diff = abs(y1 - y2)
        if diff == 0:
            return 0.0
        if diff <= YEAR_TOLERANCE:
            return 0.05 * diff
        return 0.3
    except ValueError:
        return 0.0


def find_best_match(
    album: AlbumRow,
    cache: dict[str, list[MbCandidate]],
    prefix_index: dict[str, list[str]],
) -> tuple[MbCandidate | None, float]:
    """
    album_reference 1건에 대해 MusicBrainz 최적 후보를 반환.

    매칭 점수 = 앨범명 유사도 * 0.6 + 아티스트명 유사도 * 0.4 - 연도 페널티

    1단계: exact match로 후보 좁히기
    2단계: prefix 인덱스로 같은 앞 2글자 키만 유사도 비교 (전체 순회 제거)
    """
    norm_artist = normalize(album.artist_name)

    # 크롤링 소스에서 앨범명이 "아티스트명: 앨범명" 형식인 경우 → 접두사 제거
    title = album.album_title
    if ":" in title:
        prefix, rest = title.split(":", 1)
        if string_similarity(normalize(prefix), norm_artist) >= 0.8:
            title = rest.strip()
    norm_title = normalize(title)

    # 1단계: 정확한 아티스트 키로 후보 좁히기
    candidates = list(cache.get(norm_artist, []))

    # 2단계: prefix 인덱스로 같은 앞 2글자 키만 비교 (오탈자 대응)
    if not candidates:
        prefix = norm_artist[:2] if len(norm_artist) >= 2 else norm_artist
        for key in prefix_index.get(prefix, []):
            if key != norm_artist and string_similarity(norm_artist, key) >= 0.7:
                candidates.extend(cache[key])

    if not candidates:
        return None, 0.0

    best: MbCandidate | None = None
    best_score = 0.0

    for c in candidates:
        artist_sim = string_similarity(norm_artist, normalize(c.artist_name))
        norm_release = normalize(c.release_name)
        title_sim  = string_similarity(norm_title, norm_release)

        # 한쪽이 다른쪽을 포함하면 보너스 (부제목, 접두사 차이 대응)
        if norm_title and norm_release:
            if norm_title in norm_release or norm_release in norm_title:
                title_sim = max(title_sim, 0.9)

        penalty = year_penalty(album.release_year, c.release_date)
        score   = title_sim * 0.6 + artist_sim * 0.4 - penalty

        if score > best_score:
            best_score = score
            best = c

    return best, round(best_score, 3)


# ---------------------------------------------------------------------------
# Supabase 읽기 / 쓰기
# ---------------------------------------------------------------------------

def fetch_unmatched(sb_conn, limit: int | None) -> list[AlbumRow]:
    """mb_matched = false인 album_reference 행을 가져온다."""
    sql = """
        SELECT id, raw_id, artist_name, album_title, release_year
        FROM album_reference
        WHERE mb_matched = false
        ORDER BY artist_name, album_title
    """
    if limit:
        sql += f" LIMIT {limit}"

    cur = sb_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(sql)
    rows = cur.fetchall()
    return [
        AlbumRow(
            id=str(row["id"]),
            raw_id=str(row["raw_id"]),
            artist_name=row["artist_name"],
            album_title=row["album_title"],
            release_year=row["release_year"],
        )
        for row in rows
    ]


def upsert_match(
    sb_conn,
    album_id: str,
    candidate: MbCandidate,
    score: float,
    matched: bool,
) -> None:
    sql = """
        UPDATE album_reference SET
            mb_release_id       = %s,
            mb_artist_id        = %s,
            mb_release_group_id = %s,
            mb_release_date     = %s,
            mb_country          = %s,
            mb_matched          = %s,
            mb_match_score      = %s,
            mb_matched_at       = %s
        WHERE id = %s
    """
    cur = sb_conn.cursor()
    cur.execute(sql, (
        candidate.mb_release_id,
        candidate.mb_artist_id,
        candidate.mb_release_group_id,
        candidate.release_date,
        candidate.country,
        matched,
        score,
        datetime.now(timezone.utc),
        album_id,
    ))


def mark_no_match(sb_conn, album_id: str) -> None:
    """후보가 없거나 임계값 미달인 경우: mb_matched=false, score=0으로 기록"""
    sql = """
        UPDATE album_reference SET
            mb_matched      = false,
            mb_match_score  = 0,
            mb_matched_at   = %s
        WHERE id = %s
    """
    cur = sb_conn.cursor()
    cur.execute(sql, (datetime.now(timezone.utc), album_id))


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def run(dry_run: bool, limit: int | None) -> None:
    log.info("=== build_album_reference 시작 (dry_run=%s, limit=%s) ===", dry_run, limit)

    mb_conn = psycopg2.connect(MB_DB_URL)
    mb_conn.set_session(readonly=True, autocommit=True)

    try:
        # 1. MusicBrainz 재즈 앨범 캐시 (시간이 걸리므로 Supabase 연결 전에 수행)
        cache, prefix_index = build_mb_jazz_cache(mb_conn)
    finally:
        mb_conn.close()

    sb_conn = psycopg2.connect(SUPABASE_DB_URL)

    try:
        # 2. 미매칭 앨범 목록
        albums = fetch_unmatched(sb_conn, limit)
        log.info("매칭 대상: %d건", len(albums))

        matched_count   = 0
        unmatched_count = 0
        BATCH_SIZE = 500

        for i, album in enumerate(albums):
            candidate, score = find_best_match(album, cache, prefix_index)
            matched = candidate is not None and score >= MATCH_THRESHOLD

            if dry_run:
                status = "MATCH" if matched else "NO_MATCH"
                log.info(
                    "[%s] %.3f | %s - %s → %s",
                    status, score,
                    album.artist_name, album.album_title,
                    f"{candidate.artist_name} / {candidate.release_name}" if candidate else "-",
                )
            else:
                if candidate:
                    upsert_match(sb_conn, album.id, candidate, score, matched)
                else:
                    mark_no_match(sb_conn, album.id)

                if (i + 1) % BATCH_SIZE == 0:
                    sb_conn.commit()
                    log.info("진행: %d / %d (매칭: %d)", i + 1, len(albums), matched_count + (1 if matched else 0))

            if matched:
                matched_count += 1
            else:
                unmatched_count += 1

        if not dry_run:
            sb_conn.commit()
            log.info("최종 커밋 완료")

        log.info(
            "=== 완료 | 매칭 성공: %d / 미매칭: %d / 전체: %d ===",
            matched_count, unmatched_count, len(albums),
        )

    except Exception:
        if not dry_run:
            sb_conn.rollback()
        log.exception("오류 발생, 롤백")
        sys.exit(1)

    finally:
        sb_conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MusicBrainz → album_reference 매칭 스크립트")
    parser.add_argument("--dry-run", action="store_true", help="매칭 결과만 출력, DB 저장 안 함")
    parser.add_argument("--limit",   type=int, default=None, help="처리할 최대 건수 (기본: 전체)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(dry_run=args.dry_run, limit=args.limit)
