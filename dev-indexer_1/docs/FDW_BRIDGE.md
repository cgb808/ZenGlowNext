# Postgres FDW Bridge: Supabase ⇄ Timescale on ZFS

Goal: Keep write-heavy, time-series data (events hypertable) on bare-metal TimescaleDB while allowing Supabase to read/join via postgres_fdw with operator pushdown for pgvector.

## Enable and Link

Run in Supabase Postgres (SQL editor):

```sql
-- 1) Enable FDW
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- 2) Create server link to your Timescale node
CREATE SERVER events_ts_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host '<TIMESCALE_HOST>', port '5432', dbname '<DB_NAME>');

-- 3) User mapping (consider a read-only user)
CREATE USER MAPPING FOR current_user
  SERVER events_ts_server
  OPTIONS (user '<RO_USER>', password '<RO_PASSWORD>');

-- 4) Foreign table (ghost) for events
CREATE FOREIGN TABLE events_remote (
  event_time timestamptz,
  user_token text,
  agent_key text,
  device_key text,
  location_key text,
  event_type text,
  data_payload_raw jsonb,
  data_payload_proc jsonb,
  event_embedding vector(768)
)
SERVER events_ts_server
OPTIONS (schema_name 'public', table_name 'events');

-- 5) Foreign table for activity_log (remote on Timescale)
CREATE FOREIGN TABLE remote_activity_log (
  event_time timestamptz,
  agent_id bigint,
  mission_id bigint,
  action text,
  details jsonb
)
SERVER events_ts_server
OPTIONS (schema_name 'public', table_name 'activity_log');
```

Optional: Import multiple tables with IMPORT FOREIGN SCHEMA if the remote exposes a dedicated schema for FDW.

## Vector Operator Pushdown

When pgvector exists on the remote Timescale server and the vector index lives there, queries like `<=>` similarity are pushed down automatically:

```sql
-- Find nearest events on the REMOTE server
WITH q AS (
  SELECT ARRAY[0.01, 0.02, 0.03, /* ... 768 dims ... */]::vector AS v
)
SELECT event_time, user_token, event_type,
       (events_remote.event_embedding <=> q.v) AS distance
FROM events_remote, q
WHERE events_remote.event_embedding IS NOT NULL
ORDER BY distance
LIMIT 10;
```

The heavy lifting runs on the Timescale host; Supabase only receives the top-k rows. This keeps network traffic tiny and latency low.

## Security Notes

- Prefer a read-only DB user for the FDW mapping.
- Restrict remote host firewall to Supabase egress IPs (or a WireGuard tunnel).
- Avoid exposing PII over FDW; keep PII in a separate vault DB. Join via pseudonymous tokens only.

## Maintenance
## Federated Join Example

This query runs on Supabase but joins a local table to the remote activity log living on Timescale:

```sql
SELECT
  m.id,
  m.outcome,
  ral.event_time,
  ral.action
FROM
  public.missions m  -- LOCAL (Supabase)
JOIN
  public.remote_activity_log ral ON m.id = ral.mission_id  -- REMOTE (Timescale)
WHERE
  m.id = 12345;
```

Tip: ensure appropriate indexes on `mission_id` in `activity_log` partitions for efficient joins.
- Recreate the foreign table if the remote schema changes in incompatible ways.
- Monitor `postgres_fdw` logs for pushdown effectiveness; ensure `EXPLAIN` shows foreign scan with remote conditions.
