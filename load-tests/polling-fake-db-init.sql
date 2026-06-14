CREATE TABLE IF NOT EXISTS user_reviews (
    id                      SERIAL PRIMARY KEY,
    user_id                 VARCHAR(255),
    track_name              VARCHAR(255),
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
    track_name,
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
    'Polling Load Test Track ' || n,
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
