-- Partitioned metrics (daily by default) with BRIN and basic indexes

-- Parent table
create table if not exists public.metrics (
  id bigint generated always as identity,
  device_id uuid not null,
  recorded_at timestamptz not null,
  metric_name text not null,
  metric_value double precision,
  metadata jsonb,
  created_at timestamptz default now(),
  primary key (id, recorded_at)
)
partition by range (recorded_at);

-- BRIN index on parent guides children (Postgres creates per-partition as needed)
create index if not exists idx_metrics_recorded_at_brin on public.metrics using brin (recorded_at);
create index if not exists idx_metrics_device_id on public.metrics (device_id);

-- RLS as per Supabase defaults (policies to be added per project auth model)
alter table public.metrics enable row level security;

-- Helper function to ensure a daily partition exists
create or replace function public.ensure_metrics_partition(p_day date)
returns void language plpgsql as $$
declare
  start_ts timestamptz := p_day::timestamptz;
  end_ts   timestamptz := (p_day + 1)::timestamptz;
  part_name text := format('metrics_%s', to_char(p_day, 'YYYY_MM_DD'));
  exists bool;
begin
  select exists (
    select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = part_name
  ) into exists;
  if not exists then
    execute format(
      'create table public.%I partition of public.metrics for values from (%L) to (%L)',
      part_name, start_ts, end_ts
    );
  end if;
end; $$;

-- Convenience: create partitions for a date range [start, end) daily
create or replace function public.ensure_metrics_partitions(p_start date, p_end date)
returns void language plpgsql as $$
declare d date;
begin
  d := p_start;
  while d < p_end loop
    perform public.ensure_metrics_partition(d);
    d := d + 1;
  end loop;
end; $$;

-- Optional: Hourly partitioning helpers (use only if you have very high volume per day)
create or replace function public.ensure_metrics_partition_hour(p_day date, p_hour int)
returns void language plpgsql as $$
declare
  start_ts timestamptz := (p_day + make_interval(hours => p_hour))::timestamptz;
  end_ts   timestamptz := (p_day + make_interval(hours => p_hour + 1))::timestamptz;
  part_name text := format('metrics_%s_%s', to_char(p_day, 'YYYY_MM_DD'), lpad(p_hour::text, 2, '0'));
  exists bool;
begin
  select exists (
    select 1 from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname = part_name
  ) into exists;
  if not exists then
    execute format(
      'create table public.%I partition of public.metrics for values from (%L) to (%L)',
      part_name, start_ts, end_ts
    );
  end if;
end; $$;

create or replace function public.ensure_metrics_partitions_hourly(p_day date)
returns void language plpgsql as $$
declare h int;
begin
  for h in 0..23 loop
    perform public.ensure_metrics_partition_hour(p_day, h);
  end loop;
end; $$;

-- =============================================================
-- Sanity Verification Queries (run manually)
-- =============================================================
-- Table exists
SELECT relname FROM pg_class WHERE relname='metrics' AND relkind='r';

-- RLS status
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class c
WHERE relname='metrics';

-- Parent & partition children
SELECT inhparent::regclass AS parent, inhrelid::regclass AS child
FROM pg_inherits
WHERE inhparent='public.metrics'::regclass
ORDER BY child;

-- Indexes
SELECT indexrelid::regclass AS index_name, indisvalid, indisready
FROM pg_index
WHERE indrelid='public.metrics'::regclass
ORDER BY index_name;

-- BRIN summary (blocks correlation heuristic)
SELECT * FROM brin_metapage_info('public.idx_metrics_recorded_at_brin') LIMIT 1;

-- Row counts (parent only vs including partitions)
SELECT 'parent_only' AS scope, count(*) FROM ONLY public.metrics
UNION ALL
SELECT 'all_partitions', count(*) FROM public.metrics;

-- Recent sample (latest 10)
SELECT id, device_id, recorded_at, metric_name, metric_value
FROM public.metrics
ORDER BY recorded_at DESC
LIMIT 10;

-- Partition creation dry run for next 3 days (execute to create)
-- SELECT public.ensure_metrics_partitions(current_date, current_date + 3);

-- Hourly partitions for today (only if needed)
-- SELECT public.ensure_metrics_partitions_hourly(current_date);
