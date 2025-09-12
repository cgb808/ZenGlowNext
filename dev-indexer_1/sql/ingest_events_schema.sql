-- Ingest events journal (Postgres)
create table if not exists ingest_events (
  id bigserial primary key,
  ts timestamptz not null default now(),
  channel text not null,
  event text,
  batch_tag text,
  status text,
  processed int,
  bytes bigint,
  count int,
  pii boolean,
  message jsonb not null
);
create index if not exists ix_ingest_events_ts on ingest_events (ts desc);
create index if not exists ix_ingest_events_channel_ts on ingest_events (channel, ts desc);
create index if not exists ix_ingest_events_batch_tag on ingest_events (batch_tag);

-- Optional: BRIN index for very large append-only tables (compact range scans)
create index if not exists ix_ingest_events_ts_brin on ingest_events using brin (ts);

-- PII gate lock
create table if not exists pii_gate_lock (
  scope text primary key,
  is_open boolean not null default false,
  updated_at timestamptz not null default now()
);


-- select create_hypertable('ingest_events','ts', if_not_exists => true);

-- Optional: declarative partitioning by day (useful when volume is very high)
-- Uncomment to partition; remember to create child tables via helpers/cron.
-- alter table ingest_events partition by range (ts);
