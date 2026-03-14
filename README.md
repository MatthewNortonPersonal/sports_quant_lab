# Sports Quant Lab

A quantitative sports trading operation focused on live in-game NBA markets on Kalshi, with a long-term goal of migrating models to NCAAW where markets are less efficient.

**Core thesis:** Model the score differential during a basketball game as a stochastic process (Brownian motion with drift). Derive real-time win probabilities from the model. Compare model output to Kalshi's live contract prices. Trade when there's a meaningful discrepancy.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Git

### Setup

```bash
# 1. Fork this repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/sports-quant-lab.git
cd sports-quant-lab

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the environment file (ask David for the actual API keys)
cp .env.example .env

# 4. Initialize the database
python -m infra.db.init_db

# 5. Load historical data (requires the historical loader to be implemented)
python -m infra.nba.historical_loader --league NBA --season 2024-25

# 6. Open JupyterLab and start with the first notebook
jupyter lab notebooks/01_data_exploration.ipynb
```

---

## Who Does What

### David (infra)
Owns `infra/` — Kalshi WebSocket listener, NBA live poller, database layer, orchestrator.
Uses Claude Code to build and maintain all production code.

### Matthew (quant)
Owns `notebooks/` and `notebooks/helpers/model.py`.

**Matthew's workflow:**
1. Explore data in numbered notebooks (`01_`, `02_`, ...)
2. Derive and test model functions in notebooks
3. Once a function is validated, extract a clean version into `notebooks/helpers/model.py`
4. Push to your fork — David will review and pull the model functions into the live infra

**Your notebooks are your workspace. Work freely. Commit often.**

---

## Repository Structure

```
sports-quant-lab/
├── README.md
├── requirements.txt
├── .env.example                  # Kalshi API keys, config
├── .gitignore
│
├── infra/                        # David's engineering code
│   ├── kalshi/
│   │   ├── ws_listener.py        # Kalshi WebSocket client
│   │   ├── rest_client.py        # Kalshi REST API wrapper
│   │   └── utils.py              # Fee calc, implied prob, edge ✅
│   │
│   ├── nba/
│   │   ├── live_poller.py        # Live game state from nba_api
│   │   ├── historical_loader.py  # Bulk PBP loader (NBA + NCAAW)
│   │   └── utils.py              # Clock parsing, elapsed minutes ✅
│   │
│   ├── db/
│   │   ├── schema.sql            # SQLite schema ✅
│   │   ├── init_db.py            # Database init script ✅
│   │   └── queries.py            # All DB access functions ✅
│   │
│   └── orchestrator.py           # Main pipeline entry point
│
├── notebooks/                    # Matthew's workspace
│   ├── 01_data_exploration.ipynb     # ✅ Ready to run (after data load)
│   ├── 02_parameter_estimation.ipynb # Matthew creates this
│   ├── 03_model_calibration.ipynb    # Matthew creates this
│   ├── 04_model_validation.ipynb     # Matthew creates this
│   ├── 05_market_comparison.ipynb    # Matthew creates this
│   └── helpers/
│       └── model.py              # Clean model functions (bridge to infra) ✅
│
├── data/                         # Local only — gitignored
│   ├── quant_lab.db              # SQLite database
│   └── raw/                      # CSV/JSON dumps for ad hoc analysis
│
├── tests/
│   ├── test_model.py             # ✅ Model math tests
│   ├── test_kalshi_utils.py      # ✅ Fee and pricing tests
│   └── test_db_queries.py        # ✅ Query function tests
│
├── memory/
│   └── current-status.md         # Session continuity (Claude Code)
│
└── .claude/
    └── commands/                 # Custom Claude Code slash commands
        ├── estimate-sigma.md     # /estimate-sigma
        ├── backtest-model.md     # /backtest-model
        ├── load-season.md        # /load-season
        ├── check-edge.md         # /check-edge
        ├── kalshi-fees.md        # /kalshi-fees
        ├── compare-leagues.md    # /compare-leagues
        ├── sanity-check.md       # /sanity-check
        └── fresh-eyes.md         # /fresh-eyes
```

---

## The Model

### Score Differential as Brownian Motion

```
dX(t) = μ dt + σ dW(t)

where:
  X(t)  = home score − away score at time t
  μ     = drift (points per minute) = pre_game_spread / 48
  σ     = volatility (points per √minute) — estimated from historical PBP
  W(t)  = standard Brownian motion
```

### Win Probability

```
P(home wins) = Φ((X(t) + μτ) / (σ√τ))

where:
  τ = time remaining in minutes
  Φ = standard normal CDF
```

Implemented in `notebooks/helpers/model.py:win_probability()`.

### Edge

```
edge = model_probability − kalshi_mid_price − taker_fee

taker_fee = 0.07 × P × (1 − P)
```

Positive edge = buy signal. Maker orders (limit) are fee-free but not guaranteed to fill.

---

## Database Schema

SQLite at `data/quant_lab.db`. Five tables:

| Table | Purpose |
|---|---|
| `teams` | Team reference data (league, abbreviation, pace, net rating) |
| `games` | Game reference data (date, teams, pre-game spread, status) |
| `play_by_play` | Historical PBP events (for model calibration) |
| `kalshi_snapshots` | Kalshi market prices from WebSocket listener |
| `live_snapshots` | Paired (game state + market price) rows — key table |

Full schema in [infra/db/schema.sql](infra/db/schema.sql).

**All database access goes through `infra/db/queries.py`. No raw SQL anywhere else.**

---

## Running Tests

```bash
pytest tests/ -v
```

Run before committing any changes to `infra/` or `notebooks/helpers/model.py`.

---

## Claude Code Commands

If you're using Claude Code (the CLI), custom slash commands are in `.claude/commands/`:

| Command | When to use |
|---|---|
| `/fresh-eyes` | Start of every session — re-orients Claude on project state |
| `/estimate-sigma` | After loading new data or switching leagues |
| `/backtest-model` | After changing model parameters |
| `/load-season` | To bulk load historical PBP data |
| `/check-edge` | To analyze a night of live signals |
| `/kalshi-fees` | To evaluate whether a signal is worth trading |
| `/compare-leagues` | When working on NCAAW migration |
| `/sanity-check` | When something looks too good to be true |

---

## Key Rules

- **Never trade in prod** without `KALSHI_ENV=demo` in `.env` and explicit sign-off from David
- **All DB access through `infra/db/queries.py`** — add a function there, don't write raw SQL elsewhere
- **model.py functions must be pure** — no database access, no side effects, just math
- **Run pytest before committing** any changes to `infra/` or `model.py`
- **Validate data after every load** — check game counts, date ranges, score monotonicity

---

## Environment

```bash
# .env (copy from .env.example)
KALSHI_API_KEY_ID=...
KALSHI_PRIVATE_KEY_PATH=path/to/key.pem
KALSHI_ENV=demo        # Always start here
DB_PATH=data/quant_lab.db
```

Kalshi API credentials come from [Kalshi](https://kalshi.com) account settings. Ask David if you need access.
