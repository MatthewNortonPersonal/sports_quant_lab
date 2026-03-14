Bulk load a full season of play-by-play data into the database.

Use this when:
- Setting up the database for the first time
- Adding a new season or league
- The intern needs fresh data for modeling

Steps:

1. Confirm which league and season to load. Ask if not specified.
   - NBA seasons are formatted as '2024-25'
   - NCAAW seasons use the same format

2. Check what's already in the database to avoid re-loading:
   ```python
   from infra.db import queries
   existing = queries.get_games(DB_PATH, league=LEAGUE, season=SEASON)
   print(f"Already have {len(existing)} games for {LEAGUE} {SEASON}")
   ```

3. Run the appropriate loader:

   For NBA:
   ```python
   from infra.nba.historical_loader import HistoricalLoader
   loader = HistoricalLoader(db_path=DB_PATH)
   count = loader.load_nba_season(season=SEASON)
   ```
   - Uses nba_api PlayByPlayV2 endpoint
   - Adds ~0.6s delay between requests to avoid rate limiting
   - nba_api is unofficial — handle failures gracefully

   For NCAAW:
   ```python
   count = loader.load_ncaaw_season(season=SEASON)
   ```
   - Uses CBBpy scraping ESPN
   - Be respectful with rate limits (default delay in the loader)
   - Cache aggressively — ESPN blocks aggressive scrapers

4. Validate after loading:
   - Check game count vs. expected (NBA: ~1230 regular season games)
   - Check date range makes sense
   - Run a quick sanity check: do scores increase monotonically within games?
   - Look for games with missing quarters (incomplete PBP)

5. Report:
   - Games loaded successfully
   - Games that failed or were skipped (with reasons)
   - Date range of loaded data
   - Total PBP event count

6. After a successful load, run /estimate-sigma to update model parameters.

Rate limit notes:
- nba_api: 0.5–1s between requests. If you get 429s, increase the delay.
- CBBpy/ESPN: 1–2s between requests minimum. Do not parallelize scraping.
- If loading a full season, expect it to take 30–90 minutes.
