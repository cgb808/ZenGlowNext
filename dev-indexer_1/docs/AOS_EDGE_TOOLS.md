# AoS Edge Tools

Two lightweight scripts that operate close to the DB (Timescale/Postgres). They respect the 2x2 DSN layout; pass the appropriate DSN via `--dsn`.

- `scripts/aos_predict.py`: loads `aos_matches`, builds rolling features per player, trains a logistic regression, and prints AUC/accuracy.
- `scripts/aos_stats_report.py`: prints player stats from `aos_player_stats` (materialized view). If the MV isn’t present, it attempts to call `refresh_aos_stats()`.

Examples

```bash
# Use non-PII Timescale DSN; optionally search a schema prefix first (e.g., pii)
./scripts/aos_predict.py --dsn "$DATABASE_URL_TS" --player "Alice" --window 12

# Report top players
./scripts/aos_stats_report.py --dsn "$DATABASE_URL_TS"

# Report a single player
./scripts/aos_stats_report.py --dsn "$DATABASE_URL_TS" --player "Alice"
```

Assumptions

- Table `aos_matches(ts, season, player, opponent, faction, opponent_faction, outcome, score, meta)` exists in the DSN/search_path you point at.
- Materialized view `aos_player_stats` exists or can be built by `refresh_aos_stats()`.

Notes

- The code uses `psycopg2` (binary) as installed in this repo’s requirements.
- For PII contexts, prefer `PII_DATABASE_URL_TS` and/or `--schema pii` to ensure the correct search_path ordering.
