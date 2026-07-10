CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- mb_album: MusicBrainz 앨범 메타데이터 (추천 후보 소스)
-- ============================================================
CREATE TABLE IF NOT EXISTS mb_album (
    gid                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artist_name         VARCHAR(500),
    genres              JSONB,
    first_release_year  INT
);

-- ============================================================
-- album_reference: 앨범별 임베딩 및 메타데이터 (pgvector 검색 대상)
-- ============================================================
CREATE TABLE IF NOT EXISTS album_reference (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mb_release_group_id  UUID REFERENCES mb_album(gid),
    artist_name          VARCHAR(500),
    album_title          VARCHAR(500),
    raw_id               UUID DEFAULT gen_random_uuid(),
    embedding            vector(1536)
);

CREATE INDEX IF NOT EXISTS idx_album_reference_embedding
    ON album_reference USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- ============================================================
-- match_albums: pgvector 코사인 유사도 기반 앨범 검색 함수
-- ============================================================
CREATE OR REPLACE FUNCTION match_albums(
    query_embedding vector(1536),
    match_count     int
)
RETURNS TABLE (
    album_id          uuid,
    album_artist      text,
    album_title       text,
    critics_review_id uuid,
    similarity        float
)
LANGUAGE sql AS $$
    SELECT
        ar.id                                       AS album_id,
        ar.artist_name                              AS album_artist,
        ar.album_title                              AS album_title,
        ar.raw_id                                   AS critics_review_id,
        1 - (ar.embedding <=> query_embedding)      AS similarity
    FROM album_reference ar
    WHERE ar.embedding IS NOT NULL
    ORDER BY ar.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ============================================================
-- 더미 앨범 데이터: 100,000건, 랜덤 1536차원 임베딩
-- setseed + random()으로 재현 가능한 벡터를 집합 연산으로 생성.
-- ============================================================
INSERT INTO mb_album (gid, artist_name, genres, first_release_year)
SELECT
    gen_random_uuid(),
    'Load Test Artist ' || n,
    '["jazz"]'::jsonb,
    1960 + (n % 60)
FROM generate_series(1, 30000) AS n
WHERE NOT EXISTS (SELECT 1 FROM mb_album LIMIT 1);

INSERT INTO album_reference (mb_release_group_id, artist_name, album_title, embedding)
SELECT
    ma.gid,
    ma.artist_name,
    'Load Test Album ' || ma.n,
    v.vec
FROM (
    SELECT gid, artist_name, row_number() OVER () AS n
    FROM mb_album
) ma
CROSS JOIN LATERAL (
    SELECT array_agg((random() * 2 - 1)::float4 ORDER BY d)::vector(1536) AS vec
    FROM (SELECT setseed(ma.n::float8 / 30000), generate_series(1, 1536) AS d) s
) v
WHERE NOT EXISTS (SELECT 1 FROM album_reference LIMIT 1);

CREATE TABLE IF NOT EXISTS user_reviews (
    id                      SERIAL PRIMARY KEY,
    user_id                 VARCHAR(255),
    mb_album_gid            UUID,
    album_name              VARCHAR(255),
    artist_name             VARCHAR(255),
    review_content          TEXT NOT NULL,
    rating                  NUMERIC(3, 1),
    mood                    VARCHAR(100),
    genre                   VARCHAR(100),
    energy_level            NUMERIC(3, 2),
    bpm                     INT,
    vocal_style             VARCHAR(100),
    instrumentation         VARCHAR(500),
    is_public               BOOLEAN,
    is_featured             BOOLEAN NOT NULL DEFAULT false,
    like_count              INT NOT NULL DEFAULT 0,
    comment_count           INT NOT NULL DEFAULT 0,
    recommendation_status   VARCHAR(20) NOT NULL DEFAULT 'PENDING'
                                CHECK (recommendation_status IN ('PENDING', 'COMPLETED', 'FAILED')),
    review_embedding        vector(1536),
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recommend_album (
    id                      SERIAL PRIMARY KEY,
    user_review_id          INT NOT NULL REFERENCES user_reviews(id) ON DELETE CASCADE,
    album_id                UUID NOT NULL,
    critics_review_id       UUID NOT NULL,
    album_artist            VARCHAR(255),
    album_title             VARCHAR(255),
    recommendation_score    NUMERIC(5, 4) NOT NULL,
    recommendation_reason   TEXT NOT NULL,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_recommend_album_review_album UNIQUE (user_review_id, album_id)
);

CREATE INDEX IF NOT EXISTS idx_user_reviews_recommendation_status
    ON user_reviews(recommendation_status);
CREATE INDEX IF NOT EXISTS idx_user_reviews_created_at
    ON user_reviews(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommend_album_user_review_id
    ON recommend_album(user_review_id);

INSERT INTO user_reviews (
    user_id,
    album_name,
    artist_name,
    review_content,
    rating,
    mood,
    genre,
    energy_level,
    bpm,
    vocal_style,
    instrumentation,
    is_public,
    recommendation_status
)
SELECT
    'polling-load-test-user',
    'Polling Load Test Album ' || n,
    'Jazzmate Load Test',
    'A spacious modal performance with a warm bass line and restrained cymbal texture.',
    4.5,
    'calm',
    'jazz',
    0.55,
    96,
    'instrumental',
    'piano, bass, drums',
    false,
    'PENDING'
FROM generate_series(1, 1000) AS n
WHERE NOT EXISTS (SELECT 1 FROM user_reviews);
