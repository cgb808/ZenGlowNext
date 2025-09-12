# Dev TODO (Working List)

## 0. Local Supabase (Standalone Postgres + APIs) Bootstrap

Goal: Spin up a local Supabase stack (Postgres + API) for development before wiring dual-DB production model.

### Option A: Official Supabase Docker Compose (Recommended)
1. Clone the templates repo (or ensure you have `supabase` CLI installed):
   - Install CLI: `npm install -g supabase`
2. Initialize project (if not already):
   - `supabase init`
3. Start services:
   - `supabase start`
4. Access Studio: http://localhost:54323 (default)
5. Postgres connection string (default credentials):
   - `postgresql://postgres:postgres@localhost:54322/postgres`
6. Stop services:
   - `supabase stop`

### Option B: Minimal Standalone Postgres Emulating Supabase Core
Use this only when you need a quick Postgres without the rest of Supabase APIs.

```
# Data dirs (adjust path as needed)
mkdir -p ./volumes/supa_core_pg

docker run -d \
  --name supa-core-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=postgres \
  -p 54322:5432 \
  -v $(pwd)/volumes/supa_core_pg:/var/lib/postgresql/data \
  postgres:16
```

### Option C: Supabase All-in-One Docker (Single Container)
Not officially supported for production; fine for quick local prototyping.

```
# WARNING: This image may lag behind multi-container releases.
# Replace <TAG> with a known release if needed.
# If an "all-in-one" meta image isn't available, prefer Option A.
```

### After Startup
- Apply core schema: `./scripts/db_apply.sh core` (if script prepared for core DB)
- Apply PII schema: `./scripts/db_apply.sh pii` (if using separate instance)
- Or both: `./scripts/db_apply.sh both`

### Environment Variables Reference (Local Dev)
```
SUPABASE_DB_URL=postgresql://postgres:postgres@localhost:54322/postgres
PII_DATABASE_URL=postgresql://postgres:postgres@localhost:54323/rag_pii   # if separate
DATABASE_URL=${SUPABASE_DB_URL}
STRICT_ENV=false
```

### Next Steps Planned
- Add docker compose profile for dual DB (core + pii)
- Integrate startup wait script for embedding worker in compose
- Add schema verification CI step (psql diff check)

---

(Existing TODO items will follow below this inserted section.)
