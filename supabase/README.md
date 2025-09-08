# Supabase Integration

This directory contains Supabase-specific assets:

- `functions/llm` - Edge Function proxying prompts to the Ollama host (preferred name; formerly `llm-proxy`).
  (Legacy: `functions/llm-proxy` still supported if present.)
- `migrations/` - SQL migrations to enable pgvector + Timescale and create RAG core tables.
- `kong.yml` - Local development Kong gateway configuration.

## Prerequisites
- Supabase account & project (or self-hosted stack)
- Supabase CLI installed: https://supabase.com/docs/guides/cli
- Access to a Postgres instance with `vector` and `timescaledb` extensions (Supabase hosted projects support these on qualifying tiers; for local/self-host enable in docker compose)

## Initial Setup
```
supabase link --project-ref <PROJECT_REF>
# (Optional) login first: supabase login

# Push migrations
supabase db push

# Set required secrets for Edge Function
supabase secrets set MODEL_URL=https://your-ollama-host.example.com MODEL_NAME="gemma:2b" ALLOW_ORIGIN=https://your-app.example.com

# Deploy Edge Function
supabase functions deploy llm-proxy
```

## Local Development
Create `supabase/.env.local`:
```
MODEL_URL=http://127.0.0.1:11434
MODEL_NAME=gemma:2b
ALLOW_ORIGIN=*
```
Serve the function locally (hot reload):
```
supabase functions serve llm-proxy --env-file supabase/.env.local
```
Invoke:
```
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello model"}' \
  http://localhost:54321/functions/v1/llm  (or /llm-proxy if using legacy name)
```

## Database Objects
Run `supabase db pull` after remote changes to sync schema.
Key objects:
- `doc_embeddings` (vector(768))
- `device_metrics` (hypertable)
- `search_doc_embeddings(query_embedding vector, top_k int)` helper function.

## Security & Hardening
- Current RLS policies allow public SELECT and restrict INSERT to `service_role`. Tighten for production.
- Add API key / JWT verification logic to `llm-proxy` (check `Authorization` header) before forwarding.
- Consider rate limiting (middleware or counting tokens in KV / table).

## Next Steps
1. Add an authenticated variant of the proxy with usage metering.
2. Add migrations for memory ingestion dedup table if moving ingestion into Supabase.
3. Integrate RPC for RAG query (SQL function returning top_k + optional metadata).
4. Add a migration version tracker script to ensure FastAPI app and DB schema stay aligned.

