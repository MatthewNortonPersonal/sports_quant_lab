"""
All database access for the quant lab goes through this module.

No raw SQL anywhere else in the codebase — add a function here instead.
All read functions return pandas DataFrames. Write functions return None.
"""

import sqlite3
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------

def get_teams(db_path: str, league: Optional[str] = None) -> pd.DataFrame:
    """Return all teams, optionally filtered by league."""
    sql = "SELECT * FROM teams"
    params: list = []
    if league:
        sql += " WHERE league = ?"
        params.append(league)
    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def upsert_team(
    db_path: str,
    team_id: str,
    league: str,
    name: str,
    abbreviation: Optional[str] = None,
    pace_season_avg: Optional[float] = None,
    net_rating: Optional[float] = None,
) -> None:
    """Insert or replace a team record."""
    sql = """
        INSERT OR REPLACE INTO teams
            (team_id, league, name, abbreviation, pace_season_avg, net_rating, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """
    with _connect(db_path) as conn:
        conn.execute(sql, (team_id, league, name, abbreviation, pace_season_avg, net_rating))
        conn.commit()


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------

def get_games(
    db_path: str,
    league: Optional[str] = None,
    season: Optional[str] = None,
    status: Optional[str] = None,
) -> pd.DataFrame:
    """Return games, optionally filtered by league, season, or status."""
    conditions: list[str] = []
    params: list = []
    if league:
        conditions.append("league = ?")
        params.append(league)
    if season:
        conditions.append("season = ?")
        params.append(season)
    if status:
        conditions.append("status = ?")
        params.append(status)

    sql = "SELECT * FROM games"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY game_date"

    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def upsert_game(
    db_path: str,
    game_id: str,
    league: str,
    season: Optional[str] = None,
    game_date: Optional[str] = None,
    home_team_id: Optional[str] = None,
    away_team_id: Optional[str] = None,
    pre_game_spread: Optional[float] = None,
    pre_game_total: Optional[float] = None,
    status: str = "scheduled",
) -> None:
    """Insert or replace a game record."""
    sql = """
        INSERT OR REPLACE INTO games
            (game_id, league, season, game_date, home_team_id, away_team_id,
             pre_game_spread, pre_game_total, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _connect(db_path) as conn:
        conn.execute(sql, (
            game_id, league, season, game_date, home_team_id, away_team_id,
            pre_game_spread, pre_game_total, status,
        ))
        conn.commit()


def update_game_final_score(
    db_path: str,
    game_id: str,
    home_final_score: int,
    away_final_score: int,
) -> None:
    """Mark a game as final and record the final score."""
    sql = """
        UPDATE games
        SET home_final_score = ?, away_final_score = ?, status = 'final'
        WHERE game_id = ?
    """
    with _connect(db_path) as conn:
        conn.execute(sql, (home_final_score, away_final_score, game_id))
        conn.commit()


# ---------------------------------------------------------------------------
# Play-by-play
# ---------------------------------------------------------------------------

def get_play_by_play(db_path: str, game_id: str) -> pd.DataFrame:
    """Return all PBP events for a single game, ordered by event_index."""
    sql = """
        SELECT * FROM play_by_play
        WHERE game_id = ?
        ORDER BY event_index
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=[game_id])


def get_play_by_play_for_sigma(
    db_path: str,
    league: str,
    season: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return PBP data formatted for sigma estimation.

    Joins with games so we can filter by league/season, and returns only the
    columns needed for volatility estimation: game_id, elapsed_minutes, score_margin.
    """
    conditions = ["g.league = ?"]
    params: list = [league]
    if season:
        conditions.append("g.season = ?")
        params.append(season)

    sql = f"""
        SELECT p.game_id, p.elapsed_minutes, p.score_margin, p.quarter
        FROM play_by_play p
        JOIN games g ON p.game_id = g.game_id
        WHERE {' AND '.join(conditions)}
          AND p.elapsed_minutes IS NOT NULL
          AND p.score_margin IS NOT NULL
        ORDER BY p.game_id, p.elapsed_minutes
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def insert_play_by_play_batch(db_path: str, events: list[dict]) -> int:
    """
    Insert a batch of PBP events. Returns the number of rows inserted.

    Each dict in events should have keys matching the play_by_play columns
    (excluding `id`): game_id, event_index, quarter, game_clock,
    elapsed_minutes, event_type, description, home_score, away_score,
    score_margin, scoring_team_id.
    """
    sql = """
        INSERT OR IGNORE INTO play_by_play
            (game_id, event_index, quarter, game_clock, elapsed_minutes,
             event_type, description, home_score, away_score, score_margin,
             scoring_team_id)
        VALUES
            (:game_id, :event_index, :quarter, :game_clock, :elapsed_minutes,
             :event_type, :description, :home_score, :away_score, :score_margin,
             :scoring_team_id)
    """
    with _connect(db_path) as conn:
        cursor = conn.executemany(sql, events)
        conn.commit()
        return cursor.rowcount


# ---------------------------------------------------------------------------
# Kalshi snapshots
# ---------------------------------------------------------------------------

def get_kalshi_snapshots(
    db_path: str,
    game_id: str,
    ticker: Optional[str] = None,
) -> pd.DataFrame:
    """Return Kalshi snapshots for a game, optionally filtered by ticker."""
    conditions = ["game_id = ?"]
    params: list = [game_id]
    if ticker:
        conditions.append("kalshi_ticker = ?")
        params.append(ticker)

    sql = f"""
        SELECT * FROM kalshi_snapshots
        WHERE {' AND '.join(conditions)}
        ORDER BY timestamp
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def insert_kalshi_snapshot(
    db_path: str,
    game_id: str,
    kalshi_ticker: str,
    contract_type: str,
    timestamp: str,
    bid: Optional[float],
    ask: Optional[float],
    mid: Optional[float],
    last_price: Optional[float],
    volume: Optional[int],
    is_closing: bool = False,
) -> None:
    """Write a single Kalshi market snapshot."""
    sql = """
        INSERT INTO kalshi_snapshots
            (game_id, kalshi_ticker, contract_type, timestamp, bid, ask, mid,
             last_price, volume, is_closing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _connect(db_path) as conn:
        conn.execute(sql, (
            game_id, kalshi_ticker, contract_type, timestamp, bid, ask, mid,
            last_price, volume, int(is_closing),
        ))
        conn.commit()


# ---------------------------------------------------------------------------
# Live snapshots
# ---------------------------------------------------------------------------

def get_live_snapshots(db_path: str, game_id: str) -> pd.DataFrame:
    """Return all live snapshots for a game, ordered by timestamp."""
    sql = """
        SELECT * FROM live_snapshots
        WHERE game_id = ?
        ORDER BY timestamp
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=[game_id])


def get_edge_signals(
    db_path: str,
    min_abs_edge: float = 0.05,
    since: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return live snapshots where abs(edge) exceeds the threshold.

    Args:
        db_path: Path to the database.
        min_abs_edge: Minimum absolute edge to return (default 0.05 = 5%).
        since: ISO timestamp string — only return signals after this time.
    """
    conditions = ["ABS(edge) >= ?"]
    params: list = [min_abs_edge]
    if since:
        conditions.append("timestamp >= ?")
        params.append(since)

    sql = f"""
        SELECT ls.*, g.home_team_id, g.away_team_id, g.pre_game_spread
        FROM live_snapshots ls
        JOIN games g ON ls.game_id = g.game_id
        WHERE {' AND '.join(conditions)}
        ORDER BY ABS(ls.edge) DESC
    """
    with _connect(db_path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


def insert_live_snapshot(
    db_path: str,
    game_id: str,
    timestamp: str,
    quarter: int,
    game_clock: str,
    elapsed_minutes: float,
    home_score: int,
    away_score: int,
    score_margin: int,
    kalshi_ticker: str,
    kalshi_mid: float,
    kalshi_bid: Optional[float],
    kalshi_ask: Optional[float],
    model_win_prob: Optional[float] = None,
    model_sigma: Optional[float] = None,
    model_drift: Optional[float] = None,
    edge: Optional[float] = None,
) -> None:
    """Write a single paired (game state + market) snapshot."""
    sql = """
        INSERT INTO live_snapshots
            (game_id, timestamp, quarter, game_clock, elapsed_minutes,
             home_score, away_score, score_margin,
             kalshi_ticker, kalshi_mid, kalshi_bid, kalshi_ask,
             model_win_prob, model_sigma, model_drift, edge)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _connect(db_path) as conn:
        conn.execute(sql, (
            game_id, timestamp, quarter, game_clock, elapsed_minutes,
            home_score, away_score, score_margin,
            kalshi_ticker, kalshi_mid, kalshi_bid, kalshi_ask,
            model_win_prob, model_sigma, model_drift, edge,
        ))
        conn.commit()
