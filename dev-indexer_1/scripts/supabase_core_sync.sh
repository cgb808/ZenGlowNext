#!/usr/bin/env bash
set -euo pipefail

# Apply core schemas to a Supabase Postgres instance.
# Supports either SUPABASE_DB_URL or deriving via `supabase status`.
# Files applied in order (if present):
#  - sql/artifact_a_schema.sql
#  - sql/rag_core_schema.sql
#  - sql/rag_indexes.sql
#  - sql/dev_knowledge_graph_schema.sql (optional)
#  - sql/inference_logging.sql (optional)
#  - sql/pii_vector_schema.sql (optional)
# Safe to re-run (IF NOT EXISTS guards recommended by files).

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SQL_DIR="$ROOT_DIR/sql"

apply_file() {
  local file="$1"
  if [[ -f "$file" ]]; then
    echo "[core-sync] applying $(basename "$file")"
    psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$file"
  fi
}

# Resolve DB_URL
if [[ -n "${SUPABASE_DB_URL:-}" ]]; then
  DB_URL="$SUPABASE_DB_URL"
else
  if ! command -v supabase >/dev/null 2>&1; then
    echo "supabase CLI not found and SUPABASE_DB_URL not set" >&2
    exit 2
  fi
  echo "[core-sync] Deriving DB URL from supabase CLI..."
  DB_URL=$(supabase status 2>/dev/null | awk -F': ' '/DB URL/{print $2}' | head -n1)
  if [[ -z "$DB_URL" ]]; then
    echo "Could not derive DB URL from supabase status; set SUPABASE_DB_URL explicitly" >&2
    exit 3
  fi
fi

# Apply in order
apply_file "$SQL_DIR/artifact_a_schema.sql"
apply_file "$SQL_DIR/rag_core_schema.sql"
apply_file "$SQL_DIR/rag_indexes.sql"
apply_file "$SQL_DIR/dev_knowledge_graph_schema.sql"
apply_file "$SQL_DIR/inference_logging.sql"
apply_file "$SQL_DIR/pii_vector_schema.sql"

echo "[core-sync] Complete"
