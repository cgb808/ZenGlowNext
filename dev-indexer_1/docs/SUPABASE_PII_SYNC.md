## Supabase PII Schema Sync (Staging)

Purpose: Apply the baseline (non-hardened) PII staging tables to the Supabase Postgres instance you already have CLI auth for.

### Files
- `sql/pii_secure_schema.sql` – table + index + comments (tagged with `[PII]`).
- `scripts/supabase_pii_sync.sh` – idempotent applicator.

### Prerequisites
1. Supabase CLI installed (`supabase --version`).
2. Logged in: `supabase login` (already done per your note).
3. In project directory (where `supabase/config.toml` lives) OR export `SUPABASE_DB_URL` directly.

### Run
Using CLI project context:
```
./scripts/supabase_pii_sync.sh
```
Using explicit URL:
```
SUPABASE_DB_URL=postgres://user:pass@host:5432/db ./scripts/supabase_pii_sync.sh
```

### What It Does
- Executes only `sql/pii_secure_schema.sql` (safe to re-run; IF NOT EXISTS guards).
- Does NOT enable RLS or encryption yet (keeps normal security until operational hardening phase).
- Adds audit table `pii_access_log` (metadata only) – you can start writing entries without policy overhead.

### Next Hardening (deferred)
When ready:
1. Enable RLS and add masking view(s).
2. Introduce role mapping + session variable (`SET app.current_user`).
3. Add pgcrypto / external KMS for selected columns.
4. Create trigger to populate `pii_access_log` on SELECT/UPDATE via SECURITY DEFINER function + event triggers (optional).

### Verification Query
After running:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'pii_identity_profiles'
ORDER BY ordinal_position;
```

### Safety Notes
- Keep freeform data out of `meta`; move anything sensitive into explicit columns to enforce classification.
- Rotate credentials before enabling encryption to avoid re-encrypt migration complexity.

---
Baseline only; proceed with hardening steps once operational flows stabilize.