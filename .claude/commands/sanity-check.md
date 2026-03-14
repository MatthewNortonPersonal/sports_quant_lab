Adversarial pass on model output, data quality, or trade logic.

Run this proactively before trusting any result, especially if:
- A signal looks too good (edge > 15% is almost always a bug, not real)
- Model is producing extreme probabilities (> 98% or < 2%) mid-game
- Something "feels off" about the data or results
- A new data load just completed
- Model parameters were just changed

Run all of the following checks:

---

### 1. Data quality

Check play_by_play table:
```python
from infra.db import queries
pbp = queries.get_play_by_play(DB_PATH, game_id=GAME_ID)

# Scores should never decrease
assert (pbp['home_score'].diff().fillna(0) >= 0).all(), "Home score decreased!"
assert (pbp['away_score'].diff().fillna(0) >= 0).all(), "Away score decreased!"

# Score margin = home - away
assert (pbp['score_margin'] == pbp['home_score'] - pbp['away_score']).all()

# No duplicate event indices
assert pbp['event_index'].nunique() == len(pbp)

# Elapsed minutes should be increasing
assert (pbp['elapsed_minutes'].diff().fillna(0) >= 0).all()
```

Check for missing quarters (gap > 12 minutes with no events):
```python
gaps = pbp['elapsed_minutes'].diff()
large_gaps = gaps[gaps > 12]
if not large_gaps.empty:
    print(f"WARNING: Large time gaps in PBP: {large_gaps}")
```

---

### 2. Model parameter sanity

```python
from notebooks.helpers.model import win_probability

# σ sanity: NBA should be ~1.5–2.0
if not (1.4 <= sigma <= 2.2):
    print(f"WARNING: σ = {sigma} is outside expected NBA range [1.4, 2.2]")

# Win probability at 0 time remaining
assert win_probability(5, 0, 0, 1.7) == 1.0
assert win_probability(-5, 0, 0, 1.7) == 0.0
assert win_probability(0, 0, 0, 1.7) == 0.5

# Monotonicity: more time remaining = more uncertainty
p1 = win_probability(10, 5, 0, 1.7)
p2 = win_probability(10, 15, 0, 1.7)
assert p1 > p2, "Closer to end should = higher certainty for leading team"
```

---

### 3. Kalshi price checks

Look at live_snapshots or the current Kalshi prices:
- Any prices below 3¢ or above 97¢? These are likely stale or illiquid.
- Is the bid-ask spread > 5¢? If so, the "mid" is not reliable.
- Are prices changing at all? Stale WebSocket connection?

```python
snapshots = queries.get_live_snapshots(DB_PATH, game_id=GAME_ID)
spread = snapshots['kalshi_ask'] - snapshots['kalshi_bid']
print(f"Avg bid-ask spread: {spread.mean():.3f}")
print(f"Price range: {snapshots['kalshi_mid'].min():.2f} – {snapshots['kalshi_mid'].max():.2f}")
```

---

### 4. Edge distribution sanity

```python
signals = queries.get_edge_signals(DB_PATH, min_abs_edge=0.0)
print(f"Edge stats:")
print(signals['edge'].describe())

# Red flags
n_suspicious = (signals['edge'].abs() > 0.15).sum()
if n_suspicious > 0:
    print(f"WARNING: {n_suspicious} signals with |edge| > 15% — likely a bug")
```

---

### 5. Edge cases the model must handle

- Overtime: time_remaining = 0 with score tied → should return 0.5
- Very small time_remaining (< 0.1 min): probability should be nearly 1 or 0 for any lead
- Large margins late in games: probability should approach 1.0 or 0.0 smoothly

---

Report: list of checks passed, any warnings or failures, and recommended action for each failure.
