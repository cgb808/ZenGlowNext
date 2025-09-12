#!/usr/bin/env bash
set -euo pipefail

# dev_kg_schema_verify.sh
# Run sanity / integrity checks for the Development Knowledge Graph schema.
# Optionally show a recent event sample and limit sample size.
#
# REQUIREMENTS:
#   - Supabase CLI installed & authenticated
#   - dev_knowledge_graph_schema.sql applied
#
# USAGE:
#   ./scripts/dev_kg_schema_verify.sh --project-ref ABCDEF --plan
#   ./scripts/dev_kg_schema_verify.sh --project-ref ABCDEF --recent 15
#   ./scripts/dev_kg_schema_verify.sh --project-ref ABCDEF --recent 5 --sql-out kg_check.sql
#
# FLAGS:
#   --project-ref REF   Supabase project ref (required unless cwd already linked)
#   --recent N          Include a sample of N latest development_log rows (default 10)
#   --plan              Print SQL only, do not execute
#   --sql-out PATH      Write generated SQL to file
#   -h|--help           Help
#
# EXIT CODES:
#   0 success | 2 arg error | 3 supabase cli missing | 4 execution failure

PROJECT_REF=""
RECENT=10
PLAN=0
SQL_OUT=""

usage() { sed -n '1,/^$/p' "$0"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-ref) PROJECT_REF="$2"; shift 2 ;;
    --recent) RECENT="$2"; shift 2 ;;
    --plan) PLAN=1; shift ;;
    --sql-out) SQL_OUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

HAS_SUPABASE=0
if command -v supabase >/dev/null 2>&1; then
  if supabase db --help 2>/dev/null | grep -q "query"; then
    HAS_SUPABASE=1
  fi
fi
if (( HAS_SUPABASE == 0 )); then
  if ! command -v psql >/dev/null 2>&1; then
    echo "Neither 'supabase db query' nor 'psql' available. Install psql or upgrade Supabase CLI." >&2
    exit 3
  fi
fi

read -r -d '' CORE_SQL <<SQL
-- =============================================================
-- Dev Knowledge Graph Verification (auto-generated)
-- Timestamp: $(date -Iseconds)
-- =============================================================

-- 1. Extension
SELECT 'extension' AS section, extname, extversion FROM pg_extension WHERE extname='vector';

-- 2. Tables present
SELECT 'tables' AS section, relname FROM pg_class
WHERE relnamespace='public'::regnamespace
  AND relkind='r'
  AND relname IN ('project_missions','project_epics','source_documents','code_chunks','development_log','log_to_chunk_link')
ORDER BY relname;

-- 3. Primary keys
SELECT 'primary_keys' AS section, c.relname AS table, con.conname, pg_get_constraintdef(con.oid) AS def
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
WHERE con.contype='p' AND c.relname IN ('project_missions','project_epics','source_documents','code_chunks','development_log','log_to_chunk_link')
ORDER BY table;

-- 4. Foreign keys
SELECT 'foreign_keys' AS section, c.relname AS table, con.conname, pg_get_constraintdef(con.oid) AS def
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
WHERE con.contype='f' AND c.relname IN ('project_epics','code_chunks','development_log','log_to_chunk_link')
ORDER BY table;

-- 5. Index names (filtered)
SELECT 'indexes' AS section, indexrelid::regclass AS index_name
FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid
WHERE t.relname IN ('development_log','code_chunks','log_to_chunk_link')
  AND indexrelid::regclass::text SIMILAR TO '(dev_log_epic_idx|dev_log_type_outcome_time_idx|dev_log_embedding_idx|code_chunks_doc_id_idx|code_chunks_embedding_idx|code_chunks_doc_line_uniq|log_to_chunk_link_time_idx|log_to_chunk_link_chunk_idx)%'
ORDER BY 2;

-- 6. Vector columns
SELECT 'vector_columns' AS section, table_name, column_name, udt_name
FROM information_schema.columns
WHERE table_name IN ('development_log','code_chunks') AND udt_name='vector'
ORDER BY table_name, column_name;

-- 7. Code chunk constraints
SELECT 'code_chunk_constraints' AS section, conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid='code_chunks'::regclass AND contype='c'
ORDER BY conname;

-- 8. Functions
SELECT 'functions' AS section, proname
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public' AND proname IN ('search_code_chunks','get_narrative_for_complex_code')
ORDER BY proname;

-- 9. Row counts
SELECT 'row_counts' AS section, * FROM (
  SELECT 'development_log' AS table, count(*)::bigint AS ct FROM development_log
  UNION ALL SELECT 'code_chunks', count(*) FROM code_chunks
  UNION ALL SELECT 'log_to_chunk_link', count(*) FROM log_to_chunk_link
) t;

-- 10. FK integrity (orphan epic refs)
SELECT 'fk_integrity' AS section, COUNT(*) AS missing_epic
FROM development_log dl LEFT JOIN project_epics pe ON pe.id=dl.epic_id
WHERE dl.epic_id IS NOT NULL AND pe.id IS NULL;

-- 11. Recent sample events
SELECT 'recent_events' AS section, id, occurred_at, event_type, title, outcome
FROM development_log
ORDER BY occurred_at DESC
LIMIT ${RECENT};
SQL

FINAL_SQL="$CORE_SQL"

if [[ -n "$SQL_OUT" ]]; then
  printf '%s\n' "$FINAL_SQL" >"$SQL_OUT"
fi

if (( PLAN == 1 )); then
  echo "--- PLAN (SQL only) ---"
  printf '%s\n' "$FINAL_SQL"
  exit 0
fi

if (( HAS_SUPABASE == 1 )); then
  CMD=(supabase db query)
  if [[ -n "$PROJECT_REF" ]]; then
    CMD+=(--project-ref "$PROJECT_REF")
  fi
  printf '%s\n' "$FINAL_SQL" | "${CMD[@]}" || { echo "Execution failed" >&2; exit 4; }
else
  DSN="${DATABASE_URL:-}"
  if [[ -z "$DSN" ]]; then
    if [[ -n "${PGHOST:-}" && -n "${PGPORT:-}" && -n "${PGUSER:-}" && -n "${PGDATABASE:-}" ]]; then
      PASS_PART=""
      if [[ -n "${PGPASSWORD:-}" ]]; then PASS_PART=":${PGPASSWORD}"; fi
      DSN="postgresql://${PGUSER}${PASS_PART}@${PGHOST}:${PGPORT}/${PGDATABASE}";
    fi
  fi
  if [[ -z "$DSN" ]]; then
    echo "No DATABASE_URL or discrete PG env vars set." >&2; exit 3
  fi
  printf '%s\n' "$FINAL_SQL" | PGPASSWORD="${PGPASSWORD:-}" psql "$DSN" -v ON_ERROR_STOP=1 || { echo "Execution failed" >&2; exit 4; }
fi

echo "Dev KG verification complete."
