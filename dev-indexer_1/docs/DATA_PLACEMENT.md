# Data Placement Guide: Supabase vs Timescale on ZFS

This guide summarizes where each table should live and why, and how they interact via postgres_fdw.

## Roles
- Supabase (Engagement Layer): Front office & command center. Real-time APIs, users, swarms, missions, results. Extensions: `postgres_fdw`, optional `pg_partman` + `pg_cron` for small partitions.
- Timescale on ZFS (Data Engine): Engine room & archive. High-throughput ingestion and analytics for time-series. Extensions: `timescaledb`, `pgvector`.

## Table split
- Supabase (local):
  - `swarms`, `agents`, `missions`
  - `agent_performance_stats`, `agent_ancestry_and_traits`
  - `knowledge_graph`
  - `users` (PII vault concept; join via pseudonymous tokens only)
  - `pii_token_map` (maps user_token -> identity_id with rotation windows)
- Timescale (remote):
  - `events` (hypertable)
  - `activity_log` (native partitioned; optional small mirror in Supabase if needed)

## The Bridge (FDW)
- Install `postgres_fdw` on Supabase.
- Create a server mapping to the Timescale node.
- Expose remote tables in Supabase as foreign tables: `events_remote`, `remote_activity_log`.
- Joins from Supabase can seamlessly mix local and remote tables.

## Example: Federated Join
```
SELECT m.id, m.outcome, ral.event_time, ral.action
FROM public.missions m
JOIN public.remote_activity_log ral ON m.id = ral.mission_id
WHERE m.id = 12345;
```

## Security & Ops
- Use read-only credentials for FDW mapping; restrict network to Supabase egress IPs or VPN.
- Keep PII separate; only pseudonymous keys traverse FDW.
- See `docs/PII_ARCHITECTURE.md` for vault vs token-map guidance and embeddings/retention policies.
- Monitor query plans for operator pushdown (especially vector searches) and partition pruning on `activity_log`.
