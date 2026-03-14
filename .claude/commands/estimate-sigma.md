Re-estimate the volatility parameter σ from historical play-by-play data.

Use this when:
- New historical data has been loaded into the database
- Switching between leagues (NBA → NCAAW)
- Testing time-varying or team-specific sigma
- The model calibration results look off

Steps:

1. Ask which league and season to use (NBA or NCAAW, default to whatever is in the database).

2. Load the play-by-play data:
   ```python
   from infra.db import queries
   pbp = queries.get_play_by_play_for_sigma(DB_PATH, league=LEAGUE, season=SEASON)
   ```

3. Compute 1-minute margin changes within each game:
   - Sort by (game_id, elapsed_minutes)
   - Bucket elapsed_minutes into integer minute bins
   - Take the last score_margin reading per (game_id, minute_bucket)
   - Compute first differences within each game: `df.groupby('game_id')['score_margin'].diff()`
   - Drop nulls (first row per game has no previous value)

4. Estimate σ:
   - `sigma = changes.std()`
   - This is σ in units of points per √minute
   - For NBA, expect σ ≈ 1.5–2.0. Flag anything outside this range as suspicious.

5. Optionally break down sigma by:
   - Quarter (Q1–Q4) — does volatility change late in games?
   - Game competitiveness (close vs. blowout) — does σ decay in garbage time?
   - Team pace tier — do fast-paced games have higher σ?

6. Report:
   - Overall σ estimate
   - 95% confidence interval (bootstrap if needed)
   - Sample size (number of game-minutes)
   - Any per-quarter or per-context breakdown if requested
   - Comparison to the current value in notebooks/helpers/model.py

7. If the estimate looks valid, update the σ default in notebooks/helpers/model.py or tell the user the value to set.

Sanity checks:
- NBA σ should be in [1.4, 2.2]. Flag anything outside this.
- NCAAW σ may differ — compare with /compare-leagues before updating.
- Make sure you're estimating on a held-out set, not the same data you'll trade on.
