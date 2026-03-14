Re-scan the project state after a break or at the start of a new session.

Run this at the beginning of every session to re-orient before doing any work.

Steps:

1. Read the session continuity file:
   - Read `memory/current-status.md` for the latest state
   - Note: what's built, what's running, latest model params, any open questions

2. Check recent git activity:
   ```bash
   git log --oneline -20
   git diff HEAD~5..HEAD --stat
   ```
   - Were there recent commits from Matthew (notebook work)?
   - Were there recent commits from David (infra changes)?
   - Any merge conflicts or unresolved issues?

3. Scan Matthew's notebooks for new results:
   - Look for recently modified .ipynb files
   - Check the last few cells for outputs, parameter estimates, or TODO notes
   - Has he updated any values in notebooks/helpers/model.py?

4. Check database state:
   ```python
   from infra.db import queries
   games = queries.get_games(DB_PATH)
   print(f"Total games: {len(games)}")
   print(f"By league: {games['league'].value_counts().to_dict()}")
   print(f"By season: {games['season'].value_counts().to_dict()}")

   # Check for recent live data
   import pandas as pd
   live = queries.get_edge_signals(DB_PATH, min_abs_edge=0.0)
   if not live.empty:
       print(f"Most recent live snapshot: {live['timestamp'].max()}")
   ```

5. Check if any infra is running:
   - Is the Kalshi WebSocket listener active? (check for recent kalshi_snapshots entries)
   - Is the NBA live poller collecting data? (check for recent live_snapshots)
   - Any error logs that need attention?

6. Summarize the session state in a clean format:

   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   PROJECT STATUS — [date]
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Data:        [X NBA games, Y NCAAW games, date range]
   Model:       σ = [value], last calibrated [date]
   Live pipe:   [running / not running / unknown]
   Last signal: [timestamp and edge if any]

   Matthew's last work: [notebook, what he found]
   David's last work:   [infra change, what was done]

   OPEN ITEMS:
   - [item 1]
   - [item 2]
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

7. Update `memory/current-status.md` with today's session start state.

8. Suggest the most important next action based on the current state.
