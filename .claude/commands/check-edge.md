Analyze live_snapshots data to find where the model disagrees with the market.

Use this when:
- Reviewing a night of games after the live pipeline has been running
- Looking for systematic patterns in edge (e.g., does edge cluster in certain quarters?)
- Evaluating whether the model is actually finding real discrepancies
- Preparing a post-game P&L review

Steps:

1. Load edge signals above threshold (default 5%):
   ```python
   from infra.db import queries
   signals = queries.get_edge_signals(DB_PATH, min_abs_edge=0.05)
   print(f"Found {len(signals)} signals with |edge| > 5%")
   ```

2. For each signal, determine the eventual outcome:
   - Join with games table to get final score
   - label = 1 if model-favored side actually won, 0 if it lost
   - If game isn't final yet, exclude from outcome analysis

3. Summarize signals by game context:
   - By quarter (Q1–Q4): where does edge concentrate?
   - By margin bucket (close, moderate, large): are signals more common in close games?
   - By time remaining (last 10 min vs. earlier)

4. Compute P&L if we had traded every signal:
   - Taker fee = 0.07 × P × (1 − P)
   - Net P&L per contract = outcome − kalshi_mid − fee
   - Sum across all signals
   - Sharpe-like ratio: mean_pnl / std_pnl

5. Check for stale prices:
   - If Kalshi volume is low, bid-ask spread may be wide
   - A wide spread can make edge look larger than it is
   - Flag any signal where kalshi_ask - kalshi_bid > 0.05

6. Report:
   - Number of signals at each edge threshold (2%, 5%, 8%, 10%)
   - Win rate for signals (model-favored side)
   - Hypothetical P&L (taker basis)
   - Pattern breakdown by quarter / margin
   - Any suspicious signals (extreme edge, stale prices, low volume)

Red flags:
- Edge > 15% consistently → model bug or stale data, not a real signal
- Win rate on signals < 40% → model is systematically wrong somewhere
- All signals in one quarter → possible data timing issue
