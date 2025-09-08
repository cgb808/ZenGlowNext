#!/usr/bin/env bash
set -euo pipefail

# Apply the staging PII schema (`sql/pii_secure_schema.sql`) to a Supabase
# Postgres instance using existing CLI auth or a direct DB URL.
#
# Usage (with supabase CLI project context):
#   ./scripts/supabase_pii_sync.sh
#
# Usage (direct DB URL, skips CLI):
#   SUPABASE_DB_URL=postgres://user:pass@host:5432/db ./scripts/supabase_pii_sync.sh
#
# The script prefers a direct DB URL if provided; otherwise attempts to derive
# a connection string via `supabase status` (requires you be inside a Supabase
# project directory with prior `supabase login`).
#
# Normal security posture only (no RLS/masking yet). Safe to re-run (IF NOT EXISTS guards).

SCHEMA_FILE="sql/pii_secure_schema.sql"
if [[ ! -f "$SCHEMA_FILE" ]]; then
  echo "Schema file not found: $SCHEMA_FILE" >&2
  exit 1
fi

if [[ -n "${SUPABASE_DB_URL:-}" ]]; then
  echo "[pii-sync] Applying schema via SUPABASE_DB_URL"
  psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE"
  echo "[pii-sync] Done"
  exit 0
fi

if ! command -v supabase >/dev/null 2>&1; then
  echo "supabase CLI not found and SUPABASE_DB_URL not set" >&2
  exit 2
fi

echo "[pii-sync] Deriving DB URL from supabase CLI..."
DB_URL=$(supabase status 2>/dev/null | awk -F': ' '/DB URL/{print $2}' | head -n1)
if [[ -z "$DB_URL" ]]; then
  echo "Could not derive DB URL from supabase status; set SUPABASE_DB_URL explicitly" >&2
  exit 3
fi

echo "[pii-sync] Applying schema to Supabase project"
psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE"
echo "[pii-sync] Complete"
