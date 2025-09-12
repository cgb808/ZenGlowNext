#!/usr/bin/env bash
set -euo pipefail

# Apply core schema files to existing Postgres containers (core and PII).
# Use when the data directories already exist and init scripts didn't run.
#
# Usage:
#   ./scripts/db_apply.sh [core|pii|both]
#
# Env overrides (optional):
#   CORE_CONT=rag_postgres_db
#   CORE_DB=rag_db
#   PII_CONT=rag_postgres_db_pii
#   PII_DB=rag_pii
#   PGUSER=postgres
#   PGPASSWORD=... (or rely on ident inside container)

TARGET=${1:-both}

CORE_CONT=${CORE_CONT:-rag_postgres_db}
CORE_DB=${CORE_DB:-rag_db}
PII_CONT=${PII_CONT:-rag_postgres_db_pii}
PII_DB=${PII_DB:-rag_pii}
PGUSER=${PGUSER:-postgres}

root_dir=$(cd "$(dirname "$0")/.." && pwd)
sql_dir="$root_dir/sql"

apply_sql() {
  local container="$1" dbname="$2" sql_file="$3"
  if [[ ! -f "$sql_file" ]]; then
    echo "[skip] $sql_file (not found)" >&2
    return 0
  fi
  echo "[apply] $container:$dbname <- $(basename "$sql_file")"
  docker exec -i "$container" psql -U "$PGUSER" -d "$dbname" -v ON_ERROR_STOP=1 -f - <"$sql_file"
}

apply_core() {
  # Minimal set to structure core DB for this app
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/00_init_extensions.sql" || true
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/events_unified_schema.sql"
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/41_ingestion_manifest.sql"
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/inference_logging.sql"
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/family_schema.sql"
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/family_rls.sql"
  apply_sql "$CORE_CONT" "$CORE_DB" "$sql_dir/optional_brin_indexes.sql"
}

apply_pii() {
  apply_sql "$PII_CONT" "$PII_DB" "$sql_dir/pii_secure_schema.sql"
}

case "$TARGET" in
  core) apply_core ;;
  pii) apply_pii ;;
  both) apply_core; apply_pii ;;
  *) echo "Usage: $0 [core|pii|both]"; exit 1 ;;
esac

echo "Done."
