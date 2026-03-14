# Current Project Status

_Update this file at the end of every session. Use /fresh-eyes to read it at the start._

---

## Last Updated
2026-03-13 — Initial repo setup

## What's Built

### Infrastructure (complete scaffolding)
- `infra/db/schema.sql` — SQLite schema (teams, games, play_by_play, kalshi_snapshots, live_snapshots)
- `infra/db/init_db.py` — Database initialization script (run once)
- `infra/db/queries.py` — All DB access functions (fully implemented)
- `infra/kalshi/utils.py` — Fee calculation, implied probability, edge computation (implemented)
- `infra/kalshi/rest_client.py` — Kalshi REST client (stub — auth not yet implemented)
- `infra/kalshi/ws_listener.py` — Kalshi WebSocket listener (stub — not yet implemented)
- `infra/nba/utils.py` — Game clock parsing, elapsed minutes computation (implemented)
- `infra/nba/live_poller.py` — NBA live game state poller (stub — not yet implemented)
- `infra/nba/historical_loader.py` — Historical PBP loader (stub — not yet implemented)
- `infra/orchestrator.py` — Main pipeline entry point (stub — not yet implemented)

### Model (notebooks/helpers/)
- `notebooks/helpers/model.py` — Core math functions:
  - `win_probability()` ✅ implemented
  - `estimate_drift()` ✅ implemented
  - `implied_probability()` ✅ implemented
  - `kalshi_taker_fee()` ✅ implemented
  - `edge_after_fees()` ✅ implemented
  - `estimate_sigma()` ⏳ stub — Matthew to implement in 02_parameter_estimation.ipynb

### Notebooks
- `notebooks/01_data_exploration.ipynb` — Starter notebook (complete, runs once data is loaded)
- `notebooks/02_parameter_estimation.ipynb` — Not yet created (Matthew's first task)
- `notebooks/03_model_calibration.ipynb` — Not yet created
- `notebooks/04_model_validation.ipynb` — Not yet created
- `notebooks/05_market_comparison.ipynb` — Not yet created

### Tests
- `tests/test_model.py` — Full test suite for model functions ✅
- `tests/test_kalshi_utils.py` — Tests for Kalshi utilities ✅
- `tests/test_db_queries.py` — Tests for all query functions ✅

### Claude Code Commands
All 8 slash commands implemented in `.claude/commands/`:
- `/estimate-sigma`, `/backtest-model`, `/load-season`, `/check-edge`
- `/kalshi-fees`, `/compare-leagues`, `/sanity-check`, `/fresh-eyes`

---

## Model Parameters (Current)
- σ (NBA): NOT YET ESTIMATED — waiting for data load + Matthew's 02 notebook
- Drift: computed from pre_game_spread / 48 per game

## Data
- Database: NOT YET INITIALIZED (run `python -m infra.db.init_db` first)
- NBA data: None loaded yet
- NCAAW data: None loaded yet

---

## Open Items / Next Steps

**Priority 1 — Get data flowing (David):**
1. Run `python -m infra.db.init_db` to create the database
2. Implement `infra/nba/historical_loader.py` (load NBA 2024-25 season)
3. Run `/load-season` to populate play_by_play

**Priority 2 — Model calibration (Matthew):**
1. Run `notebooks/01_data_exploration.ipynb` once data is loaded
2. Create `notebooks/02_parameter_estimation.ipynb` — estimate σ
3. Implement `estimate_sigma()` in `notebooks/helpers/model.py`
4. Run `/estimate-sigma` to validate

**Priority 3 — Live pipeline (David):**
1. Implement Kalshi REST auth (`infra/kalshi/rest_client.py`)
2. Implement WebSocket listener (`infra/kalshi/ws_listener.py`)
3. Implement NBA live poller (`infra/nba/live_poller.py`)
4. Wire together in `infra/orchestrator.py`
5. Test end-to-end with `KALSHI_ENV=demo`

---

## Notes
- Kalshi ENV must stay `demo` until David explicitly authorizes prod
- All DB access must go through `infra/db/queries.py` — no raw SQL elsewhere
- Run `pytest` before committing changes to infra/ or model.py
