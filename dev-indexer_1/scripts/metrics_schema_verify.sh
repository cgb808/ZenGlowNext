#!/usr/bin/env bash
set -euo pipefail

# metrics_schema_verify.sh
# Run targeted sanity / health queries for the partitioned metrics schema on a Supabase project.
# Optionally pre-create future daily (and hourly) partitions in the same run.
#
# REQUIREMENTS:
#   - Supabase CLI installed and authenticated (supabase link OR pass --project-ref)
#   - metrics_timeseries.sql previously applied (tables + functions present)
#
# USAGE EXAMPLES:
#   ./scripts/metrics_schema_verify.sh --project-ref abcdefghij123 --plan
#   ./scripts/metrics_schema_verify.sh --project-ref abcdefghij123 --future-days 7
#   ./scripts/metrics_schema_verify.sh --project-ref abcdefghij123 --future-days 3 --hourly-today
#   ./scripts/metrics_schema_verify.sh --project-ref abcdefghij123 --sql-out metrics_check.sql
#
# FLAGS:
#   --project-ref REF     Supabase project ref (required unless already linked in cwd)
#   --future-days N       Also ensure daily partitions for [today, today+N)
#   --hourly-today        Additionally ensure all 24 hourly partitions for today
#   --plan                Print SQL only (dry run) without executing
#   --sql-out PATH        Write the generated SQL to a file (still executes unless --plan)
#   -h|--help             Help
#
# EXIT CODES:
#   0 success | 2 arg error | 3 supabase cli missing | 4 execution failure
#
# NOTE: The verification queries are read-only except optional partition creation calls.

PROJECT_REF=""
FUTURE_DAYS=0
HOURLY_TODAY=0
PLAN=0
SQL_OUT=""

usage() { sed -n '1,/^$/p' "$0"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-ref) PROJECT_REF="$2"; shift 2 ;;
    --future-days) FUTURE_DAYS="$2"; shift 2 ;;
    --hourly-today) HOURLY_TODAY=1; shift ;;
    --plan) PLAN=1; shift ;;
    --sql-out) SQL_OUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

HAS_SUPABASE=0
if command -v supabase >/dev/null 2>&1; then
  # We require a "db query" subcommand which is not present in some CLI versions.
  if supabase db --help 2>/dev/null | grep -q "query"; then
    HAS_SUPABASE=1
  fi
fi

# Fallback: use psql if Supabase CLI lacks db query.
if (( HAS_SUPABASE == 0 )); then
  if ! command -v psql >/dev/null 2>&1; then
    echo "Neither 'supabase db query' nor 'psql' available. Install psql or upgrade Supabase CLI." >&2
    exit 3
  fi
fi

# Build dynamic partition creation SQL (optional)
PARTITION_SQL=""
if (( FUTURE_DAYS > 0 )); then
  PARTITION_SQL+=$'-- Create future daily partitions\n'
  PARTITION_SQL+=$"SELECT public.ensure_metrics_partitions(current_date, current_date + $FUTURE_DAYS);\n"
fi
if (( HOURLY_TODAY == 1 )); then
  PARTITION_SQL+=$'-- Create hourly partitions for today\n'
  PARTITION_SQL+=$'SELECT public.ensure_metrics_partitions_hourly(current_date);\n'
fi

CORE_SQL=$(cat <<'SQL'
-- =============================================================
-- Metrics Schema Verification (auto-generated)
-- Timestamp: $(date -Iseconds)
-- =============================================================

-- 1. Table exists
SELECT 'table_exists' AS check, relname FROM pg_class WHERE relname='metrics' AND relkind='r';

-- 2. RLS status
SELECT 'rls_status' AS check, relname, relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE relname='metrics';

-- 3. Parent & partition children
SELECT 'partitions' AS section, inhparent::regclass AS parent, inhrelid::regclass AS child
FROM pg_inherits
WHERE inhparent='public.metrics'::regclass
ORDER BY child;

-- 4. Indexes on parent
SELECT 'indexes' AS section, indexrelid::regclass AS index_name, indisvalid, indisready
FROM pg_index
WHERE indrelid='public.metrics'::regclass
ORDER BY index_name;

-- 5. BRIN metapage info (skipped if function missing)
DO $$BEGIN
  IF to_regprocedure('brin_metapage_info(regclass)') IS NOT NULL THEN
    RAISE NOTICE 'brin_meta';
    PERFORM 1 FROM brin_metapage_info('public.idx_metrics_recorded_at_brin');
  ELSE
    RAISE NOTICE 'brin_metapage_info not available';
  END IF;
END$$;

-- 6. Row counts (parent vs all)
SELECT 'row_counts' AS section, * FROM (
  SELECT 'parent_only' AS scope, count(*)::bigint AS ct FROM ONLY public.metrics
  UNION ALL
  SELECT 'all_partitions', count(*)::bigint FROM public.metrics
) t;

-- 7. Recent sample rows
SELECT 'recent_sample' AS section, id, device_id, recorded_at, metric_name, metric_value
FROM public.metrics
ORDER BY recorded_at DESC
LIMIT 10;
SQL
)

# Compose final SQL
FINAL_SQL="$CORE_SQL"
if [[ -n "$PARTITION_SQL" ]]; then
  FINAL_SQL+=$'\n-- Optional partition operations\n'
  FINAL_SQL+="$PARTITION_SQL"
fi

# Expand the date inside the heredoc substitution (the earlier heredoc literal prevents immediate expansion)
FINAL_SQL=$(echo "$FINAL_SQL" | sed "s/\$(date -Iseconds)/$(date -Iseconds)/")

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
  # Use DATABASE_URL or discrete PG* env vars.
  DSN="${DATABASE_URL:-}"
  if [[ -z "$DSN" ]]; then
    # Assemble from discrete vars if provided
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

echo "Verification complete."
