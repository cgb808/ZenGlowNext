-- Requires pg_cron extension (Supabase supports it). Run these after creating tables.

-- Create a daily aggregate materialized view (optional)
create materialized view if not exists ingest_events_daily as
select date_trunc('day', ts) as day,
       channel,
       count(*) as events,
       count(*) filter (where event = 'gate.open') as gates_open,
       count(*) filter (where event = 'gate.done' and status = 'success') as gates_success,
       count(*) filter (where event = 'embed.start') as embeds_started
from ingest_events
group by 1,2;

create index if not exists ix_ingest_events_daily on ingest_events_daily(day desc, channel);

-- Cron: refresh daily aggregates at 01:10 UTC
select cron.schedule(
  'refresh_ingest_events_daily',
  '10 1 * * *',
  $$ refresh materialized view concurrently ingest_events_daily; $$
)
on conflict (jobname) do update set schedule = excluded.schedule, command = excluded.command;

-- Retention: keep 30 days of raw events (tune as needed)
select cron.schedule(
  'retention_ingest_events_30d',
  '0 2 * * *',
  $$ delete from ingest_events where ts < now() - interval '30 days'; $$
)
on conflict (jobname) do update set schedule = excluded.schedule, command = excluded.command;
