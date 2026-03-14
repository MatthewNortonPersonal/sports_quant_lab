
# Sports Quant Lab - Claude Instructions

## About This Project
- Two-person operation: **David** (engineer/infra) and **Matthew** (quant/modeling intern)
- David directs Claude Code to build all infrastructure, pipelines, and production code
- Matthew works exclusively in Jupyter notebooks and `notebooks/helpers/model.py`
- Core thesis: model in-game score differential as a stochastic process, derive win probabilities, compare to Kalshi contract prices, trade the discrepancy
- Starting with NBA (more data, more liquid markets), migrating to NCAAW (less efficient markets, real edge)
- All trading happens on **Kalshi** — a regulated event contract exchange, not a traditional sportsbook

## Repository Layout
- `infra/` — David's domain. Kalshi WebSocket listener, NBA live poller, historical data loader, SQLite database, orchestrator
- `notebooks/` — Intern's domain. Numbered notebooks for exploration → estimation → calibration → validation → market comparison
- `notebooks/helpers/model.py` — Clean model functions extracted from notebooks. This is the bridge between intern's math and David's infra
- `data/quant_lab.db` — Single SQLite database, source of truth for all data
- `infra/db/queries.py` — All database access goes through here. No raw SQL anywhere else

## Key Concepts (for context)
- **Score differential as Brownian motion**: dX(t) = μdt + σdW(t) where X(t) is home score minus away score
- **Win probability**: P(home wins) = Φ((margin + μτ) / (σ√τ)) where τ = time remaining
- **Drift (μ)**: pre-game spread divided by 48 minutes. Captures team strength differential
- **Volatility (σ)**: ~1.5-2 points per √minute for NBA. Estimated from historical play-by-play. Different for NCAAW
- **Kalshi pricing**: contract at 65¢ implies 65% probability. Taker fee = 0.07 × P × (1-P). Maker orders are free
- **Edge**: model_probability - kalshi_mid_price - taker_fee. Positive = buy signal
- **CLV (Closing Line Value)**: the closing price is the most efficient. Beating it consistently = skill

## Skills to Use

These are implemented as real Claude Code slash commands in `.claude/commands/`.
Type `/estimate-sigma`, `/backtest-model`, etc. to invoke them.

### /estimate-sigma
Re-estimate the volatility parameter from play-by-play data. Use when:
- New historical data has been loaded
- Switching between leagues (NBA → NCAAW)
- Testing time-varying or team-specific sigma

Workflow:
1. Query `play_by_play` table for the relevant league/season/teams
2. Compute minute-by-minute score margin changes
3. Calculate std dev of changes (this is σ)
4. Optionally break down by quarter, team pace tier, or game context
5. Update the parameter in `notebooks/helpers/model.py` or return for notebook use

### /backtest-model
Run the win probability model against historical games and check calibration. Use when:
- Model parameters have changed
- A new model variant is being tested
- Comparing two model specifications

Workflow:
1. For each game in the dataset, compute model win prob at every minute mark
2. Bucket predictions (e.g., 60-65%, 65-70%, etc.)
3. Compute actual win rate per bucket
4. Plot calibration curve (predicted vs actual). Should be close to 45° line
5. Compute Brier score as a single summary metric
6. Report where the model is over/under-confident

### /load-season
Bulk load a full season of play-by-play data. Use when:
- Setting up the database for the first time
- Adding a new season or league
- Intern needs fresh data

Workflow:
1. Determine league (NBA or NCAAW) and season
2. For NBA: use `nba_api` PlayByPlayV2 endpoint
3. For NCAAW: use `CBBpy` Scraper with `get_game_pbp()`
4. Normalize into the `play_by_play` table schema (compute `elapsed_minutes` from quarter + clock)
5. Also populate the `games` and `teams` tables
6. Report: games loaded, date range, any failures

### /check-edge
Analyze live_snapshots data to find where model disagrees with market. Use when:
- Reviewing a night of games
- Looking for systematic patterns in edge
- Evaluating whether the model is actually finding real discrepancies

Workflow:
1. Query `live_snapshots` where `abs(edge) > threshold` (default 0.05)
2. Group by game, quarter, margin bucket
3. Check if edge predictions were correct (did the model-favored side win?)
4. Look for patterns: does edge concentrate in certain game states?
5. Compute P&L if we had traded every signal above threshold

### /kalshi-fees
Calculate net edge after Kalshi fees for a potential trade. Use when:
- Evaluating whether a signal is worth trading
- Comparing maker vs taker execution
- Sizing a position

Workflow:
1. Input: model_prob, kalshi_price, order_type (maker/taker)
2. Compute taker fee: 0.07 × P × (1-P)
3. Compute edge net of fees
4. For maker orders: fee is zero, but you're not guaranteed a fill
5. Report: gross edge, fee, net edge, breakeven model prob

### /compare-leagues
Compare model parameters between NBA and NCAAW. Use when:
- Preparing for NCAAW migration
- Testing the hypothesis that NCAAW has different dynamics
- Calibrating NCAAW-specific parameters

Workflow:
1. Run /estimate-sigma for both NBA and NCAAW
2. Compare: pace, sigma, score distributions, late-game volatility
3. Identify where the biggest parameter differences are
4. These differences are where NCAAW markets are most likely mispriced if books use NBA-like assumptions

### /sanity-check
Adversarial pass on model output or trade logic. Use proactively before trusting any result. Use when:
- A signal looks too good (edge > 15% is suspicious)
- Model is producing extreme probabilities
- Something feels off about the data

Checks:
1. Is the data clean? (no duplicate PBP entries, no missing games, scores monotonically increasing)
2. Is sigma reasonable? (NBA should be ~1.5-2.0, NCAAW slightly different)
3. Does the model handle edge cases? (overtime, garbage time, 0 time remaining)
4. Are Kalshi prices stale? (low volume markets may not reflect true probability)
5. Is the edge real or is it just the bid-ask spread?

### /fresh-eyes
Re-scan the project state after a break or long session. Use when:
- Picking up after time away
- Intern has pushed new notebook work
- Starting a new session

Workflow:
1. Read `memory/current-status.md` for latest state
2. Check git log for recent commits
3. Scan notebooks for new results or parameter changes
4. Check if live data pipeline is running and collecting
5. Summarize: what's working, what's pending, what needs attention

## Code Quality
- **All database access through `infra/db/queries.py`** — no raw SQL in notebooks or infra modules
- **Type hints everywhere** in infra code
- **Notebooks should be narrative** — markdown cells explaining the math before every code cell
- **model.py functions should be pure** — no database access, no side effects, just math
- Keep infra code async (asyncio, httpx, websockets). Keep notebook code synchronous and simple
- If a notebook function is stable and tested, extract it to `model.py`
- Run `pytest` before committing any changes to `infra/` or `model.py`

## Preventing Mistakes
- **Never trade in prod without testing in Kalshi demo first** — set `KALSHI_ENV=demo` in `.env`
- **Validate data after every load** — check game counts, date ranges, score reasonableness
- **Don't overfit sigma** — estimate on training set, validate on holdout. Don't use this season's playoffs to estimate params you'll trade on this season's playoffs
- **Kalshi prices below 5¢ or above 95¢ are usually not worth trading** — the fee eats most of the edge
- **If edge is consistently > 10%, something is probably wrong with your model, not with the market**
- **NBA nba_api endpoints are unofficial and can break** — handle failures gracefully, don't crash the pipeline
- **CBBpy scrapes ESPN** — be respectful with rate limits, cache aggressively

## Memory & Session Continuity
- Use `memory/current-status.md` to track: what's built, what's running, latest model params, latest results
- Before ending a session, write a summary of what was done and what's next
- Use `/fresh-eyes` at the start of every session to re-orient
- Intern's progress lives in his notebooks — check git log for his commits to understand what he's been working on

## Working with Matthew
- His notebooks are his workspace — don't restructure them without asking
- When his model functions are ready, help him extract clean versions into `model.py`
- If he's stuck on a data issue, the fix is probably in `infra/db/queries.py` (write him a new query function)
- His math is the product — treat his derivations and parameter estimates as the source of truth for the model
