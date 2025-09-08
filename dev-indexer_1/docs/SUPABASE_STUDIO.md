## Supabase Studio (Local Dev)

Goal: Quickly browse & experiment with schema / RLS using the official Supabase open source stack (Studio + Auth + REST + Realtime) **without** replacing the existing `docker-compose.yml` for the indexer service.

### When To Use
| Scenario | Use Studio? |
|----------|-------------|
| Inspect / edit tables | Yes |
| Prototype RLS policies | Yes |
| Run auth flows (GoTrue) | Yes |
| Production deployment | No (use managed Supabase or hardened infra) |

### Launch
```
./scripts/dev_supabase_studio.sh
```
Outputs current status or spins up the stack (first run pulls images). Studio opens at:

http://localhost:54323

### Stack Ports (CLI defaults)
- Studio UI: 54323
- REST (PostgREST): 54321
- Realtime WS: 54322
- Auth (GoTrue): 9999
- Meta: 8080
- DB: 54322 (separate Postgres from existing `rag_postgres_db` on 5432)

### Using Existing Data
Option 1: Snapshot & import
```
docker exec -t rag_postgres_db pg_dump -U postgres -d rag_db > /tmp/rag_db_dump.sql
psql postgres://postgres:postgres@localhost:54322/postgres -f /tmp/rag_db_dump.sql
```

Option 2: Apply schema migrations only (clean slate): copy relevant `sql/*.sql` then run them inside the Supabase DB with `psql`.

### RLS / Policy Prototyping Flow
1. Import or create target tables.
2. Enable RLS and draft policies in Studio UI.
3. Test queries via REST endpoint with bearer tokens produced by GoTrue (simulate anon vs service keys).
4. Export final `ALTER TABLE` / `CREATE POLICY` statements back into versioned SQL files in this repo.

### Keys & Auth
After startup, CLI prints anon & service API keys. For local experiments you can set:
```
export SUPABASE_ANON_KEY=...  
export SUPABASE_SERVICE_KEY=...
```
Then call REST:
```
curl -H "apikey: $SUPABASE_ANON_KEY" \
     -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     http://localhost:54321/rest/v1/family_people
```

### Stopping / Cleanup
```
supabase stop      # stop containers (preserves volumes)
supabase db reset  # reset database (DANGEROUS: wipes data)
```

### Separation From Existing Compose
The Supabase CLI stack is isolated: different network, different Postgres (54322). This avoids interfering with `docker compose up db` which binds `127.0.0.1:5432`.

### Limitations
- Not wired into the running FastAPI container automatically (separate DB). For integration tests against Studio DB, point env vars at `localhost:54322` instead of `db`.
- Performance is dev-grade.
- Secrets/keys from CLI stack are not production-safe.

### Next Steps (Optional)
- Write a small migration sync script to capture Studio-created policies into `sql/` versioned files.
- Add test harness validating RLS semantics before promoting.

---
Use Studio strictly as a rapid prototyping surface; commit only the resulting SQL, not the transient generated config.