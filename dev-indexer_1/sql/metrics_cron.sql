-- Requires pg_cron extension

-- Create tomorrow's partition daily at 00:05 UTC
select cron.schedule(
  'metrics_part_create_tomorrow',
  '5 0 * * *',
  $$ select public.ensure_metrics_partition((now() + interval '1 day')::date); $$
)
on conflict (jobname) do update set schedule = excluded.schedule, command = excluded.command;

-- Optional: create hourly partitions for tomorrow (only if using hourly layout)
select cron.schedule(
  'metrics_part_create_tomorrow_hourly',
  '10 0 * * *',
  $$ select public.ensure_metrics_partitions_hourly((now() + interval '1 day')::date); $$
)
on conflict (jobname) do update set schedule = excluded.schedule, command = excluded.command;

-- Retention: drop partitions older than 90 days (adjust as needed)
create or replace function public.drop_old_metrics_partitions(retention_days int)
returns void language plpgsql as $$
declare
  cutoff date := (now() - make_interval(days => retention_days))::date;
  rel record;
begin
  for rel in
    select c.relname
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relname like 'metrics_%'
  loop
    -- parse date from suffix
    begin
      -- metrics_YYYY_MM_DD
      if to_date(substring(rel.relname from 'metrics_(\d{4}_\d{2}_\d{2})'), 'YYYY_MM_DD') < cutoff then
        execute format('drop table if exists public.%I cascade', rel.relname);
      end if;
    exception when others then
      -- ignore parsing errors
      null;
    end;
  end loop;
end; $$;

select cron.schedule(
  'metrics_retention_90d',
  '30 2 * * *',
  $$ select public.drop_old_metrics_partitions(90); $$
)
on conflict (jobname) do update set schedule = excluded.schedule, command = excluded.command;
