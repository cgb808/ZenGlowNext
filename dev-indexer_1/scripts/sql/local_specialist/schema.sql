-- Local Specialist/Agent Schema: detailed logs, raw swarm telemetry

create extension if not exists vector;

-- Inference events
create table if not exists model_inference_events (
  id text primary key,
  ts timestamptz default now(),
  model_name text,
  user_id text,
  prompt_tokens int,
  completion_tokens int,
  latency_ms int,
  avg_logprob double precision,
  entropy double precision,
  top1_prob double precision,
  decision text,
  meta jsonb
);
create index if not exists idx_model_inference_events_ts on model_inference_events(ts desc);
create index if not exists idx_model_inference_events_user on model_inference_events(user_id);

create table if not exists model_inference_token_stats (
  event_id text not null,
  position int not null,
  token text,
  logprob double precision,
  is_generated boolean,
  primary key(event_id, position)
);
create index if not exists idx_token_stats_event on model_inference_token_stats(event_id);

-- Full swarm events (raw)
create table if not exists swarm_events (
  id bigserial primary key,
  ts timestamptz default now(),
  event_type text,
  session_id text,
  user_hash text,
  query_text text,
  query_hash text,
  path_hash text,
  partition_id int,
  swarm_type text,
  success boolean,
  latency_ms double precision,
  quality_signal double precision,
  factors jsonb,
  parameters jsonb,
  telemetry jsonb,
  meta jsonb,
  event_embedding vector(384)
);
create index if not exists idx_swarm_events_ts on swarm_events(ts desc);
create index if not exists idx_swarm_events_type on swarm_events(event_type);
