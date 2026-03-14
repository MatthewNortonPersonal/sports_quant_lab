Run the win probability model against historical games and evaluate calibration.

Use this when:
- Model parameters have changed (new σ estimate, new drift assumption)
- A new model variant is being tested
- Comparing two model specifications side by side
- Before trusting any live edge signal

Steps:

1. Load historical games with final scores:
   ```python
   from infra.db import queries
   games = queries.get_games(DB_PATH, league=LEAGUE, status='final')
   ```

2. For each game, load play-by-play and compute win probability at every minute mark:
   ```python
   from notebooks.helpers.model import win_probability, estimate_drift

   for game_id in games['game_id']:
       pbp = queries.get_play_by_play(DB_PATH, game_id)
       drift = estimate_drift(game['pre_game_spread'])
       for minute in range(0, 48):
           # Get margin at this minute (last event before or at `minute`)
           # Compute win_probability(margin, time_remaining=48-minute, drift, sigma)
   ```

3. Build a calibration dataset:
   - Each row: (predicted_win_prob, actual_outcome)
   - actual_outcome = 1 if home team won, 0 if away team won

4. Bucket predictions into 5% bins (e.g., [0.55–0.60), [0.60–0.65), etc.)
   - For each bucket: compute predicted_mean and actual_win_rate
   - A well-calibrated model should have predicted ≈ actual across all buckets

5. Compute Brier score:
   ```python
   brier = ((predictions - actuals) ** 2).mean()
   ```
   - Lower is better. A random model scores 0.25. Target < 0.20 for this market.

6. Plot the calibration curve:
   - x-axis: predicted win probability
   - y-axis: actual win rate
   - The 45° diagonal is perfect calibration
   - Note where the model is overconfident (above diagonal) or underconfident (below)

7. Report:
   - Overall Brier score
   - Calibration curve (text table if no plotting available)
   - Worst-performing buckets
   - Sample size per bucket
   - Comparison to baseline (naive model using only pre-game spread)

Sanity checks:
- If Brier score < 0.15, something is probably leaking — check for look-ahead bias
- Make sure final scores are excluded from features at prediction time
- Use a true holdout set (e.g., last month of season) — not the same data σ was estimated on
