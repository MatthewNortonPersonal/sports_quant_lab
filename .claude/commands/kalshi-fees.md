Calculate net edge after Kalshi fees for a potential trade.

Use this when:
- Evaluating whether a live signal is worth acting on
- Comparing maker vs. taker execution strategy
- Sizing a position based on net edge
- Explaining fee impact to someone new to Kalshi

Steps:

1. Gather inputs. If not provided, ask:
   - model_prob: your model's estimated win probability (0–1)
   - kalshi_price: current mid price on Kalshi (0–1 scale)
   - order_type: 'taker' (market order, immediate fill) or 'maker' (limit order, free but may not fill)

2. Compute taker fee:
   ```python
   from infra.kalshi.utils import taker_fee
   fee = taker_fee(kalshi_price)
   # Fee = 0.07 × P × (1 − P)
   # At P=0.50: fee ≈ 0.0175 (1.75¢)
   # At P=0.65: fee ≈ 0.0159 (1.59¢)
   # At P=0.80: fee ≈ 0.0112 (1.12¢)
   ```

3. Compute gross and net edge:
   ```python
   gross_edge = model_prob - kalshi_price
   net_edge_taker = gross_edge - fee
   net_edge_maker = gross_edge  # no fee, but no guaranteed fill
   ```

4. Compute breakeven model probability:
   - For taker: model_prob_breakeven = kalshi_price + fee
   - For maker: model_prob_breakeven = kalshi_price

5. Print a clear summary table:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Model probability:   72.0%
   Kalshi mid price:    60.0%
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Gross edge:          +12.0%
   Taker fee (7%):       -1.5%
   Net edge (taker):    +10.5%  ← TRADE
   Net edge (maker):    +12.0%  ← TRADE (but no fill guarantee)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Taker breakeven:      61.5%
   Maker breakeven:      60.0%
   ```

6. Provide a recommendation:
   - Net edge > 5%: worth trading as taker
   - Net edge 2–5%: consider maker only (save the fee)
   - Net edge < 2%: pass — fee risk not worth it
   - Kalshi price < 5¢ or > 95¢: almost certainly not worth it

Notes:
- Maker orders are free but not guaranteed to fill (limit orders in the book)
- In illiquid markets, limit orders often don't fill before the game ends
- Kelly criterion for position sizing: f* = edge / (1 - price) approximately
