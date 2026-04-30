-- One row per game played — self-populating via CV watcher or API ingest
CREATE TABLE IF NOT EXISTS user_matches (
    id              SERIAL PRIMARY KEY,
    match_uid       VARCHAR(64) UNIQUE,
    player_username VARCHAR(64) NOT NULL,
    player_uid      BIGINT,
    hero_played     VARCHAR(64) NOT NULL,
    map_id          INT,
    map_name        VARCHAR(128),
    side            VARCHAR(8) CHECK (side IN ('attack', 'defense', 'unknown')),
    result          VARCHAR(8) NOT NULL CHECK (result IN ('win', 'loss', 'draw')),
    ally_heroes     TEXT[],
    enemy_comp      TEXT[],
    enemy_uids      BIGINT[],
    enemy_usernames TEXT[],
    kills           INT,
    deaths          INT,
    assists         INT,
    season          VARCHAR(16),
    game_mode_id    INT,
    played_at       TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    source          VARCHAR(8) DEFAULT 'cv'
);

-- Community win rates by rank (scraped manually or from API)
CREATE TABLE IF NOT EXISTS meta_win_rates_rank (
    id          SERIAL PRIMARY KEY,
    hero_name   VARCHAR(64) NOT NULL,
    rank_tier   VARCHAR(32) NOT NULL,
    game_mode   VARCHAR(16) NOT NULL,
    win_rate    DECIMAL(5,2),
    pick_rate   DECIMAL(5,2),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, rank_tier, game_mode)
);

-- Community win rates by map (scraped manually)
CREATE TABLE IF NOT EXISTS meta_win_rates_map (
    id          SERIAL PRIMARY KEY,
    hero_name   VARCHAR(64) NOT NULL,
    map_name    VARCHAR(128) NOT NULL,
    rank_tier   VARCHAR(32) NOT NULL DEFAULT 'All',
    win_rate    DECIMAL(5,2),
    source      VARCHAR(32),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (hero_name, map_name, rank_tier)
);

-- Map ID → name cache (from API or manually populated)
CREATE TABLE IF NOT EXISTS map_cache (
    map_id    INT PRIMARY KEY,
    map_name  VARCHAR(128) NOT NULL,
    map_type  VARCHAR(32),
    cached_at TIMESTAMPTZ DEFAULT NOW()
);

-- Every recommendation session logged for review
CREATE TABLE IF NOT EXISTS recommendation_log (
    id                 SERIAL PRIMARY KEY,
    player_username    VARCHAR(64),
    map_name           VARCHAR(128),
    side               VARCHAR(8),
    ally_heroes        TEXT[],
    detected_via       VARCHAR(16),
    llm_prompt         TEXT,
    llm_response       TEXT,
    recommended_heroes TEXT[],
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Enemy player profiles (Phase 4 — deferred)
CREATE TABLE IF NOT EXISTS enemy_profiles (
    id              SERIAL PRIMARY KEY,
    player_uid      BIGINT NOT NULL,
    player_username VARCHAR(64),
    hero_name       VARCHAR(64) NOT NULL,
    games_played    INT DEFAULT 0,
    wins            INT DEFAULT 0,
    losses          INT DEFAULT 0,
    win_rate        DECIMAL(5,2),
    season          VARCHAR(16),
    is_private      BOOLEAN DEFAULT FALSE,
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (player_uid, hero_name, season)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_matches_player     ON user_matches (player_username);
CREATE INDEX IF NOT EXISTS idx_user_matches_player_uid ON user_matches (player_uid);
CREATE INDEX IF NOT EXISTS idx_user_matches_hero       ON user_matches (hero_played);
CREATE INDEX IF NOT EXISTS idx_user_matches_map        ON user_matches (map_name);
CREATE INDEX IF NOT EXISTS idx_user_matches_side       ON user_matches (side);
CREATE INDEX IF NOT EXISTS idx_user_matches_result     ON user_matches (result);
CREATE INDEX IF NOT EXISTS idx_user_matches_ally       ON user_matches USING GIN (ally_heroes);
CREATE INDEX IF NOT EXISTS idx_meta_rank_hero          ON meta_win_rates_rank (hero_name, rank_tier);
CREATE INDEX IF NOT EXISTS idx_meta_map_hero           ON meta_win_rates_map (hero_name, map_name, rank_tier);
CREATE INDEX IF NOT EXISTS idx_enemy_profiles_uid      ON enemy_profiles (player_uid);
