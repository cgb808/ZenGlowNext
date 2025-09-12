-- Local PII Schema: user-sensitive entities

create extension if not exists vector;

-- Family entities (PII)
create table if not exists family_people (
  id text primary key,
  name text not null,
  last_name text,
  age int,
  grade_band text,
  birthdate date,
  household_id text,
  meta jsonb default '{}'::jsonb,
  created_ts timestamptz default now(),
  updated_ts timestamptz default now()
);

create table if not exists family_relationships (
  guardian_id text not null,
  child_id text not null,
  kind text not null,
  legal boolean default true,
  created_ts timestamptz default now(),
  primary key(guardian_id, child_id, kind)
);

create table if not exists family_artifacts (
  id text primary key,
  entity_id text not null,
  kind text not null,
  title text,
  tags text[] default '{}',
  content_ref text,
  meta jsonb default '{}'::jsonb,
  created_ts timestamptz default now()
);
create index if not exists idx_family_artifacts_entity on family_artifacts(entity_id);
create index if not exists idx_family_artifacts_created on family_artifacts(created_ts desc);

create table if not exists family_health_metrics (
  entity_id text not null,
  metric text not null,
  value_text text,
  value_num double precision,
  unit text,
  ts timestamptz default now(),
  primary key(entity_id, metric, ts)
);
create index if not exists idx_family_health_metrics_entity on family_health_metrics(entity_id);

-- Conversation events (PII, may include content)
create table if not exists conversation_events (
  time timestamptz default now(),
  id text primary key,
  content text,
  content_hash text,
  embedding vector(384),
  embedded boolean default false
);
create index if not exists idx_conversation_events_time on conversation_events(time desc);

-- Transcription jobs
create table if not exists transcriptions (
  job_id text primary key,
  status text,
  filename text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
