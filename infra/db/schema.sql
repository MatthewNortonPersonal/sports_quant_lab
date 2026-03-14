-- Sports Quant Lab — SQLite Schema
-- All tables support both NBA and NCAAW data.
-- Single source of truth at data/quant_lab.db

PRAGMA foreign_keys = ON;

-- Teams reference table
CREATE TABLE IF NOT EXISTS teams (
    team_id         TEXT PRIMARY KEY,       -- nba_api team ID or ESPN team ID
    league          TEXT NOT NULL,           -- 'NBA', 'NCAAW', 'WNBA'
    name            TEXT NOT NULL,
    abbreviation    TEXT,
    pace_season_avg REAL,                   -- avg possessions per game this season
    net_rating      REAL,                   -- offensive rating minus defensive rating
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Games reference table
CREATE TABLE IF NOT EXISTS games (
    game_id          TEXT PRIMARY KEY,       -- from nba_api or CBBpy
    league           TEXT NOT NULL,
    season           TEXT,                   -- e.g. '2025-26'
    game_date        DATE,
    home_team_id     TEXT REFERENCES teams(team_id),
    away_team_id     TEXT REFERENCES teams(team_id),
    home_final_score INTEGER,               -- NULL until game ends
    away_final_score INTEGER,
    pre_game_spread  REAL,                  -- home perspective, e.g. -6.5
    pre_game_total   REAL,
    status           TEXT DEFAULT 'scheduled'  -- scheduled, live, final
);

-- Historical play-by-play (for model calibration)
-- One row per scoring event or other tracked game event
CREATE TABLE IF NOT EXISTS play_by_play (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         TEXT REFERENCES games(game_id),
    event_index     INTEGER,                -- ordering within the game
    quarter         INTEGER,
    game_clock      TEXT,                   -- e.g. '05:32' remaining in quarter
    elapsed_minutes REAL,                   -- minutes since tip-off (computed)
    event_type      TEXT,                   -- 'field_goal', 'free_throw', 'turnover', etc.
    description     TEXT,
    home_score      INTEGER,
    away_score      INTEGER,
    score_margin    INTEGER,                -- home_score - away_score
    scoring_team_id TEXT
);

-- Kalshi market snapshots (written by WebSocket listener)
CREATE TABLE IF NOT EXISTS kalshi_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id       TEXT REFERENCES games(game_id),
    kalshi_ticker TEXT NOT NULL,            -- Kalshi market ticker
    contract_type TEXT,                     -- 'spread', 'total', 'moneyline'
    timestamp     TIMESTAMP NOT NULL,
    bid           REAL,                     -- best bid price (0-1 scale)
    ask           REAL,                     -- best ask price (0-1 scale)
    mid           REAL,                     -- (bid + ask) / 2
    last_price    REAL,
    volume        INTEGER,
    is_closing    INTEGER DEFAULT 0         -- 1 if last snapshot before tip-off
);

-- Live paired snapshots: game state + market price at the same moment
-- Key table for model-vs-market comparison and trade signal generation
CREATE TABLE IF NOT EXISTS live_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         TEXT REFERENCES games(game_id),
    timestamp       TIMESTAMP NOT NULL,
    -- Game state
    quarter         INTEGER,
    game_clock      TEXT,
    elapsed_minutes REAL,
    home_score      INTEGER,
    away_score      INTEGER,
    score_margin    INTEGER,
    -- Kalshi market state at this moment
    kalshi_ticker   TEXT,
    kalshi_mid      REAL,
    kalshi_bid      REAL,
    kalshi_ask      REAL,
    -- Model output (filled in by model evaluation step)
    model_win_prob  REAL,
    model_sigma     REAL,
    model_drift     REAL,
    edge            REAL                    -- model_win_prob - kalshi_mid
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_pbp_game        ON play_by_play(game_id);
CREATE INDEX IF NOT EXISTS idx_pbp_elapsed     ON play_by_play(game_id, elapsed_minutes);
CREATE INDEX IF NOT EXISTS idx_kalshi_game     ON kalshi_snapshots(game_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_live_game       ON live_snapshots(game_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_live_edge       ON live_snapshots(edge);
CREATE INDEX IF NOT EXISTS idx_games_league    ON games(league, season);
