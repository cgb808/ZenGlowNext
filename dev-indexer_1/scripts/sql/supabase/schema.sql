-- Supabase (Cloud) Schema: Non-PII general data
-- Safe to run multiple times (IF NOT EXISTS where applicable)

-- Extensions
create extension if not exists vector;
create extension if not exists pg_trgm;
create extension if not exists btree_gin;

-- RAG index
create table if not exists doc_embeddings (
  id bigserial primary key,
  source text,
  chunk text not null,
  embedding vector(384),
  created_at timestamptz default now(),
  batch_tag text,
  metadata jsonb,
  user_id uuid null
);

-- Optional text search support
alter table if exists doc_embeddings add column if not exists chunk_tsv tsvector;
create index if not exists idx_doc_embeddings_tsv on doc_embeddings using gin (chunk_tsv);
create index if not exists idx_doc_embeddings_embed on doc_embeddings using ivfflat (embedding vector_cosine_ops);
create index if not exists idx_doc_embeddings_user on doc_embeddings(user_id);

-- Trigger to maintain tsvector (simplified)
create or replace function doc_embeddings_tsv_trigger() returns trigger language plpgsql as $$
begin
  new.chunk_tsv := to_tsvector('english', coalesce(new.chunk,''));
  return new;
end$$;
create trigger trg_doc_embeddings_tsv before insert or update on doc_embeddings
for each row execute function doc_embeddings_tsv_trigger();

-- Sanitized swarm events (no raw query text)
create table if not exists swarm_events_sanitized (
  id bigserial primary key,
  ts timestamptz default now(),
  event_type text,
  session_id text,
  user_hash text,
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
  meta jsonb
);
create index if not exists idx_swarm_events_sanitized_ts on swarm_events_sanitized(ts desc);

-- RPC for vector similarity via PostgREST
-- Returns: id, chunk, distance
create or replace function match_documents(embedding vector, match_count int default 5)
returns table (id bigint, chunk text, distance double precision)
language sql stable parallel safe as $$
  select d.id, d.chunk, (d.embedding <-> embedding) as distance
  from doc_embeddings d
  where d.embedding is not null
  order by d.embedding <-> embedding
  limit match_count
$$;

-- Row Level Security (RLS) example
alter table doc_embeddings enable row level security;
create policy if not exists doc_embeddings_rls_select on doc_embeddings
  for select using (
    auth.role() = 'service_role' or user_id is null or user_id = auth.uid()
  );

-- Optional: allow inserts for service role only
create policy if not exists doc_embeddings_rls_insert on doc_embeddings
  for insert with check (auth.role() = 'service_role');
