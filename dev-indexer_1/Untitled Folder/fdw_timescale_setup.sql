-- FDW Timescale Setup (Supabase -> Remote TimescaleDB)
-- Fill <TIMESCALE_HOST>, <DB_NAME>, <RO_USER>, <RO_PASSWORD> with secure values (use Vault/env, never commit secrets).

CREATE EXTENSION IF NOT EXISTS postgres_fdw;

CREATE SERVER IF NOT EXISTS events_ts_server
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host '<TIMESCALE_HOST>', port '5432', dbname '<DB_NAME>');

CREATE USER MAPPING IF NOT EXISTS FOR CURRENT_USER
  SERVER events_ts_server
  OPTIONS (user '<RO_USER>', password '<RO_PASSWORD>');

CREATE FOREIGN TABLE IF NOT EXISTS events_remote (
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

CREATE FOREIGN TABLE IF NOT EXISTS remote_activity_log (
  event_time timestamptz,
  agent_id bigint,
  mission_id bigint,
  action text,
  details jsonb
)
SERVER events_ts_server
OPTIONS (schema_name 'public', table_name 'activity_log');

-- Sample federated query
-- SELECT m.id, m.outcome, ral.event_time, ral.action
-- FROM public.missions m
-- JOIN public.remote_activity_log ral ON m.id = ral.mission_id
-- WHERE m.id = 12345;
