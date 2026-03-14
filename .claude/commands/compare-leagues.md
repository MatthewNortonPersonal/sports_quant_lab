Compare model parameters between NBA and NCAAW to identify where markets may be mispriced.

Use this when:
- Preparing for the NCAAW migration
- Testing the hypothesis that NCAAW dynamics differ meaningfully from NBA
- Calibrating NCAAW-specific parameters (σ, pace, score distribution)
- Pitching to David why NCAAW is the better long-run opportunity

Core hypothesis:
If Kalshi prices NCAAW games using NBA-like assumptions, and NCAAW has
meaningfully different dynamics (different σ, different pace, different
late-game behavior), then there's structural edge in NCAAW markets.

Steps:

1. Load PBP data for both leagues:
   ```python
   from infra.db import queries
   pbp_nba = queries.get_play_by_play_for_sigma(DB_PATH, league='NBA')
   pbp_ncaaw = queries.get_play_by_play_for_sigma(DB_PATH, league='NCAAW')
   ```

2. Estimate σ for each league using the same methodology:
   - 1-minute margin change standard deviation
   - Report: σ_NBA, σ_NCAAW, confidence intervals

3. Compare scoring dynamics:
   - Average points per minute (pace proxy)
   - Distribution of score margins at game end
   - Overtime frequency (affects model assumptions)
   - Typical game margin trajectory (does NCAAW blow up more in Q4?)

4. Compare late-game behavior specifically:
   - σ in the last 5 minutes vs. first 5 minutes
   - "Garbage time" effect: does volatility drop when margin > 15 late?
   - Free throw rates late in close games (affects Brownian motion assumption)

5. Identify the biggest differences:
   - Where do NBA and NCAAW parameters diverge most?
   - These divergences = where Kalshi is most likely to be mispriced if using NBA assumptions

6. Report:
   - Side-by-side parameter table (σ, avg scoring rate, OT rate, etc.)
   - Key structural differences
   - Recommendation: which parameters need NCAAW-specific values?
   - Priority order for NCAAW model calibration work

Note: NCAAW games are 40 minutes (2 halves × 20 min), not 4 quarters × 12.
Make sure elapsed_minutes is computed correctly for NCAAW data and that
win_probability() is called with total_minutes=40.
