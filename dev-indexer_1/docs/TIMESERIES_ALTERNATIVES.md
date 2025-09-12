## Time-series on Postgres (Supabase-first)

Recommended default (what this repo uses):

- Native Postgres partitioning + BRIN indexes (recommended): Use declarative range partitioning (by day/hour) and BRIN indexes for compact, fast scans on append-mostly time-series data. Works without extensions and is fully supported in Supabase.

Alternatives (optional):

- Citus (distributed Postgres): If you need horizontal scaling and large write volume; requires managed hosting or a compatible extension.
- InfluxDB or ClickHouse: Separate specialized time-series stores; integrate via Edge Functions or external services if you need very high ingestion rates and specialized queries.
- Supabase + Supabase.ai embeddings: For ML-specific rolling metrics (niche).

Postgres-native pattern (what the SQL does):

- Creates a `metrics` table with:
  - `id` bigint identity primary key
  - `device_id` uuid
  - `recorded_at` timestamptz
  - `metric_name` text
  - `metric_value` double precision
  - `metadata` jsonb
- Demonstrates daily partitioning via helpers and cron jobs (with optional hourly helpers).
- Adds a BRIN index on `recorded_at` for efficient range scans.
- Adds an index on `device_id` to speed joins/filters.
- Enables Row Level Security (RLS) — add policies after creating the table.

References in this repo:

- Metrics (partitioned) schema (daily + optional hourly): `sql/metrics_timeseries.sql`
- Metrics pg_cron automation (daily + optional hourly): `sql/metrics_cron.sql`
- Ingest journal + dashboards (MV + retention): `sql/ingest_events_schema.sql`, `sql/ingest_events_cron.sql`
- Edge mirror to external TS: set `TIMESERIES_WEBHOOK_URL` in `supabase/functions/event-publish`.

Recommendation: use native Postgres partitioning + BRIN and pg_cron as the baseline. Add an external sink only when you need higher write rates or specialized analytics.
