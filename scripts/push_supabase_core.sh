#!/usr/bin/env bash
set -euo pipefail

# Push local schema + custom roles/RLS + Edge Function (llm-proxy) to an existing Supabase project.
# Prereqs:
#   1. supabase CLI installed & logged in:  supabase login
#   2. Export SUPABASE_REF (project ref, e.g. abcd1234) and SUPABASE_DB_URL (service role connection string)
#   3. (Optional) MODEL_URL / MODEL_NAME / ALLOW_ORIGIN for Edge Function secrets
# Usage:
#   SUPABASE_REF=xxxx SUPABASE_DB_URL='postgresql://...' bash scripts/push_supabase_core.sh
# Idempotent: re-runs safely; existing objects skipped via IF NOT EXISTS / DO blocks.

err() { echo "[supabase-push] ERROR: $*" >&2; exit 1; }
log() { echo "[supabase-push] $*" >&2; }

command -v supabase >/dev/null || err "supabase CLI not found"

[[ -n "${SUPABASE_REF:-}" ]] || err "Set SUPABASE_REF"
[[ -n "${SUPABASE_DB_URL:-}" ]] || err "Set SUPABASE_DB_URL (service_role DSN)"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1. Link project (creates .supabase if absent)
if ! grep -q "${SUPABASE_REF}" "$ROOT_DIR/supabase/config.toml" 2>/dev/null; then
  log "Linking project $SUPABASE_REF"
  (cd "$ROOT_DIR" && supabase link --project-ref "$SUPABASE_REF")
else
  log "Project already linked"
fi

# 2. Run standard migrations (pgvector tables, search function)
log "Applying core migrations (supabase/migrations)"
(cd "$ROOT_DIR" && supabase db push --project-ref "$SUPABASE_REF")

# 3. Apply custom roles/privileges + RLS (outside default migrations path)
log "Applying roles & privileges"
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$ROOT_DIR/dev-indexer_1/sql/roles_privileges.sql" || err "roles_privileges.sql failed"

log "Applying RLS policies (non-enforcing by default)"
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$ROOT_DIR/dev-indexer_1/sql/rls_policies.sql" || err "rls_policies.sql failed"

# 4. Set Edge Function secrets (only if provided)
if [[ -n "${MODEL_URL:-}" || -n "${MODEL_NAME:-}" || -n "${ALLOW_ORIGIN:-}" ]]; then
  log "Setting function secrets (MODEL_URL/NAME/ALLOW_ORIGIN)"
  supabase secrets set --project-ref "$SUPABASE_REF" \
    MODEL_URL="${MODEL_URL:-http://127.0.0.1:11434}" \
    MODEL_NAME="${MODEL_NAME:-gemma:2b}" \
    ALLOW_ORIGIN="${ALLOW_ORIGIN:-*}" >/dev/null
fi

# 5. Deploy Edge Function llm (preferred) else fallback to llm-proxy
if [ -d "$ROOT_DIR/supabase/functions/llm" ]; then
  log "Deploying Edge Function: llm"
  (cd "$ROOT_DIR" && supabase functions deploy llm --project-ref "$SUPABASE_REF")
elif [ -d "$ROOT_DIR/supabase/functions/llm-proxy" ]; then
  log "Deploying legacy Edge Function: llm-proxy"
  (cd "$ROOT_DIR" && supabase functions deploy llm-proxy --project-ref "$SUPABASE_REF")
else
  log "No llm or llm-proxy function directory found; skipping"
fi

# 5b. Deploy curate-code ingestion function
if [ -d "$ROOT_DIR/supabase/functions/curate-code" ]; then
  log "Deploying Edge Function: curate-code"
  (cd "$ROOT_DIR" && supabase functions deploy curate-code --project-ref "$SUPABASE_REF")
else
  log "curate-code function directory missing; skipping"
fi

# 6. Smoke test (non-auth invocation) prefer llm
if supabase functions ls --project-ref "$SUPABASE_REF" | grep -q '\bllm\b'; then
  log "Invoking llm test (no-verify-jwt)"
  supabase functions invoke llm --project-ref "$SUPABASE_REF" --no-verify-jwt --body '{"prompt":"ping"}' || log "llm invoke returned non-zero (may be expected if MODEL_URL unreachable)"
else
  log "Invoking llm-proxy test (no-verify-jwt)"
  supabase functions invoke llm-proxy --project-ref "$SUPABASE_REF" --no-verify-jwt --body '{"prompt":"ping"}' || log "llm-proxy invoke returned non-zero (may be expected if MODEL_URL unreachable)"
fi

log "Done. Next steps: set ZENDEXER_INGEST_KEY + GITHUB_PAT secrets if not already, then test curate-code with auth header." 
