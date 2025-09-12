# Embedding Processor (Supabase Edge Function)

This function locks a conversation event row, calls an external embedding service, and updates the row atomically.

## Environment Variables
- `SUPABASE_URL` – Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` – Service role key (keep secret)
- `EMBED_ENDPOINT` – External embed API (default `http://127.0.0.1:8000/model/embed`)

## Deploy

Using Supabase CLI:
```bash
supabase functions deploy embedding-processor --project-ref <PROJECT_REF>
```

Invoke example:
```bash
supabase functions invoke embedding-processor --project-ref <PROJECT_REF> --body '{"time":"2025-09-12T00:00:00Z","id":"00000000-0000-0000-0000-000000000000"}'
```

Ensure the RPC exists (apply the migration): `sql/migrations/2025-09-12/001_get_and_lock_unembedded_event.sql`
