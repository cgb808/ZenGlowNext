#!/usr/bin/env bash
set -euo pipefail

# supabase_full_sync.sh
#
# Unified (local + remote) Supabase/Postgres schema bootstrap & sync utility.
# Safely (dry-run by default) applies an ordered set of SQL schema files and
# optional modules, with integrated drift check and guarded destructive ops.
#
# FEATURES
#  - Ordered application (extensions -> base -> indexes -> optional modules)
#  - Dry-run default (shows plan)
#  - Explicit --apply flag required to modify DB
#  - Optional schema drift check (public schema) before changes
#  - Reset (drop & recreate) public schema for local / remote with confirmation
#  - Destructive statement guard unless --allow-destructive provided
#  - Skips files containing destructive patterns when guard active
#  - Logs phases; optional file log via --log-file
#
# CONNECTION RESOLUTION
#  Primary ("local") DB:
#     PRIMARY_DATABASE_URL or DATABASE_URL
#  Remote (Supabase) DB:
#     SUPABASE_DB_URL (preferred) else derived via `supabase status`
#
# RESET MODES
#  --reset-local   Drop & recreate public schema on primary DB before apply
#  --reset-remote  Drop & recreate public schema on remote DB before apply
#  Confirmation required unless --yes set.
#
# DRIFT CHECK
#  --drift-check    Run schema_drift_check.py (primary vs remote) prior to apply
#  --fatal-on-drift Exit non‑zero (3) if drift detected
#  --json-drift-out <file|-> Emit machine readable diff
#
# EXIT CODES
#  0 success | 2 config error | 3 drift abort | 4 destructive blocked | 5 apply failure
#
# USAGE EXAMPLES
#  Dry run (plan only):
#    ./scripts/supabase_full_sync.sh
#  Apply to remote (assuming SUPABASE_DB_URL set):
#    ./scripts/supabase_full_sync.sh --apply
#  Reset both schemas then apply (dangerous):
#    ./scripts/supabase_full_sync.sh --reset-local --reset-remote --apply --yes
#  Drift check only (no apply):
#    ./scripts/supabase_full_sync.sh --drift-check --json-drift-out -
#
# NOTE: Relies on IF NOT EXISTS in SQL for idempotency. Adjust ordering below
#       cautiously—earlier files may define objects referenced later.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SQL_DIR="$ROOT_DIR/sql"
SCRIPT_NAME=$(basename "$0")

log() { echo "[$SCRIPT_NAME] $*"; if [[ -n "${LOG_FILE:-}" ]]; then printf '%s %s\n' "$(date -Iseconds)" "$*" >>"$LOG_FILE"; fi; }
err() { log "ERROR: $*" >&2; }

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [flags]
  --apply                Actually apply SQL (default is plan only)
  --allow-destructive     Permit destructive statements (DROP / ALTER DROP)
  --reset-local           Drop & recreate public schema on PRIMARY (local)
  --reset-remote          Drop & recreate public schema on REMOTE (Supabase)
  --yes                   Skip interactive confirmations
  --drift-check           Run drift check prior to applying
  --fatal-on-drift        Exit if drift is detected (code 3)
  --json-drift-out PATH   Write drift JSON (use - for stdout)
  --log-file PATH         Append log output to file
  -h|--help               Show this help
EOF
}

APPLY=0
ALLOW_DESTRUCTIVE=0
RESET_LOCAL=0
RESET_REMOTE=0
YES=0
DRIFT_CHECK=0
FATAL_ON_DRIFT=0
JSON_DRIFT_OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1 ; shift ;;
    --allow-destructive) ALLOW_DESTRUCTIVE=1 ; shift ;;
    --reset-local) RESET_LOCAL=1 ; shift ;;
    --reset-remote) RESET_REMOTE=1 ; shift ;;
    --yes) YES=1 ; shift ;;
    --drift-check) DRIFT_CHECK=1 ; shift ;;
    --fatal-on-drift) FATAL_ON_DRIFT=1 ; shift ;;
    --json-drift-out) JSON_DRIFT_OUT="$2" ; shift 2 ;;
    --log-file) LOG_FILE="$2" ; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) err "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

# Resolve primary/local DSN
PRIMARY_DSN="${PRIMARY_DATABASE_URL:-${DATABASE_URL:-}}"
if [[ -z "$PRIMARY_DSN" ]]; then
  log "PRIMARY database DSN not set (PRIMARY_DATABASE_URL or DATABASE_URL) -> local operations disabled"
fi

# Resolve remote/Supabase DSN
if [[ -n "${SUPABASE_DB_URL:-}" ]]; then
  REMOTE_DSN="$SUPABASE_DB_URL"
else
  if command -v supabase >/dev/null 2>&1; then
    REMOTE_DSN=$(supabase status 2>/dev/null | awk -F': ' '/DB URL/{print $2}' | head -n1 || true)
  else
    REMOTE_DSN=""
  fi
fi

if [[ -z "$REMOTE_DSN" ]]; then
  log "Remote (Supabase) DSN not resolved; remote steps skipped unless only local requested"
fi

# When applying, we require at least one DSN to be valid
if (( APPLY == 1 )) && [[ -z "$PRIMARY_DSN" && -z "$REMOTE_DSN" ]]; then
  err "No target DSNs resolved; cannot apply"
  exit 2
fi

confirm() {
  local prompt="$1"; local resp
  if (( YES == 1 )); then return 0; fi
  read -r -p "$prompt [type YES to continue]: " resp || true
  [[ "$resp" == "YES" ]] || { err "Confirmation failed"; return 1; }
}

reset_public() {
  local dsn="$1"; local label="$2"
  log "Resetting public schema on $label"
  psql "$dsn" -v ON_ERROR_STOP=1 <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
COMMENT ON SCHEMA public IS 'standard';
SQL
}

run_drift_check() {
  if (( DRIFT_CHECK == 0 )); then return 0; fi
  if [[ -z "$PRIMARY_DSN" || -z "$REMOTE_DSN" ]]; then
    log "Drift check skipped (need both primary + remote)"; return 0
  fi
  local cmd=(python "$ROOT_DIR/scripts/schema_drift_check.py")
  (( FATAL_ON_DRIFT == 1 )) && cmd+=("--fatal-on-drift")
  if [[ -n "$JSON_DRIFT_OUT" ]]; then
    cmd+=("--json-out" "$JSON_DRIFT_OUT")
  fi
  log "Running drift check..."
  PRIMARY_DATABASE_URL="$PRIMARY_DSN" SECONDARY_DATABASE_URL="$REMOTE_DSN" "${cmd[@]}" || {
    local ec=$?
    if (( ec == 1 && FATAL_ON_DRIFT == 1 )); then
      err "Drift detected and fatal-on-drift set"
      exit 3
    fi
  }
}

contains_destructive() {
  grep -Eqi '\bDROP\s+(TABLE|INDEX|SCHEMA)|ALTER\s+TABLE\s+[^;]+\bDROP\b' "$1"
}

apply_file() {
  local file="$1"; local dsn="$2"; local mode_label="$3"
  if [[ ! -f "$file" ]]; then return 0; fi
  local base=$(basename "$file")
  if (( ALLOW_DESTRUCTIVE == 0 )) && contains_destructive "$file"; then
    log "[skip:$mode_label] $base (destructive statements present; use --allow-destructive)"; return 0
  fi
  if (( APPLY == 0 )); then
    log "[plan:$mode_label] $base"
  else
    log "[apply:$mode_label] $base"
    psql "$dsn" -v ON_ERROR_STOP=1 -f "$file" || { err "Failed applying $base"; exit 5; }
  fi
}

# ORDERING LOGIC
# Prefer consolidated_rag_schema_v2 over rag_core_schema if both present.
BASE_SCHEMA=""
if [[ -f "$SQL_DIR/consolidated_rag_schema_v2.sql" ]]; then
  BASE_SCHEMA="$SQL_DIR/consolidated_rag_schema_v2.sql"
elif [[ -f "$SQL_DIR/rag_core_schema.sql" ]]; then
  BASE_SCHEMA="$SQL_DIR/rag_core_schema.sql"
fi

FILES_BASE=()
[[ -f "$SQL_DIR/00_init_extensions.sql" ]] && FILES_BASE+=("$SQL_DIR/00_init_extensions.sql")
[[ -n "$BASE_SCHEMA" ]] && FILES_BASE+=("$BASE_SCHEMA")
[[ -f "$SQL_DIR/artifact_a_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/artifact_a_schema.sql")
[[ -f "$SQL_DIR/ingest_events_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/ingest_events_schema.sql")
[[ -f "$SQL_DIR/events_unified_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/events_unified_schema.sql")
[[ -f "$SQL_DIR/hybrid_retrieval_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/hybrid_retrieval_schema.sql")
[[ -f "$SQL_DIR/unified_discovery_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/unified_discovery_schema.sql")
[[ -f "$SQL_DIR/dev_knowledge_graph_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/dev_knowledge_graph_schema.sql")
[[ -f "$SQL_DIR/unified_knowledge_graph_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/unified_knowledge_graph_schema.sql")
[[ -f "$SQL_DIR/family_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/family_schema.sql")
[[ -f "$SQL_DIR/colony_swarm_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/colony_swarm_schema.sql")
[[ -f "$SQL_DIR/swarm_schema.sql" ]] && FILES_BASE+=("$SQL_DIR/swarm_schema.sql")
[[ -f "$SQL_DIR/swarm_repo_schema_v6.sql" ]] && FILES_BASE+=("$SQL_DIR/swarm_repo_schema_v6.sql")
[[ -f "$SQL_DIR/user_session_state.sql" ]] && FILES_BASE+=("$SQL_DIR/user_session_state.sql")
[[ -f "$SQL_DIR/inference_logging.sql" ]] && FILES_BASE+=("$SQL_DIR/inference_logging.sql")
[[ -f "$SQL_DIR/timescale_artifacts.sql" ]] && FILES_BASE+=("$SQL_DIR/timescale_artifacts.sql")
[[ -f "$SQL_DIR/metrics_timeseries.sql" ]] && FILES_BASE+=("$SQL_DIR/metrics_timeseries.sql")

# Index / supplemental stage
FILES_INDEXES=()
[[ -f "$SQL_DIR/rag_indexes.sql" ]] && FILES_INDEXES+=("$SQL_DIR/rag_indexes.sql")
[[ -f "$SQL_DIR/pgvector_indexes.sql" ]] && FILES_INDEXES+=("$SQL_DIR/pgvector_indexes.sql")
[[ -f "$SQL_DIR/add_vector_indexes.sql" ]] && FILES_INDEXES+=("$SQL_DIR/add_vector_indexes.sql")
[[ -f "$SQL_DIR/optional_brin_indexes.sql" ]] && FILES_INDEXES+=("$SQL_DIR/optional_brin_indexes.sql")

# Policies / roles last (may depend on tables existing)
FILES_SECURITY=()
[[ -f "$SQL_DIR/roles_privileges.sql" ]] && FILES_SECURITY+=("$SQL_DIR/roles_privileges.sql")
[[ -f "$SQL_DIR/rls_policies.sql" ]] && FILES_SECURITY+=("$SQL_DIR/rls_policies.sql")
[[ -f "$SQL_DIR/family_rls.sql" ]] && FILES_SECURITY+=("$SQL_DIR/family_rls.sql")

log "Plan (apply=$APPLY destructive_allowed=$ALLOW_DESTRUCTIVE reset_local=$RESET_LOCAL reset_remote=$RESET_REMOTE)"
log "Primary DSN: ${PRIMARY_DSN:-<none>}"
log "Remote  DSN: ${REMOTE_DSN:-<none>}"

run_drift_check

if (( RESET_LOCAL == 1 )) && [[ -n "$PRIMARY_DSN" ]]; then
  confirm "Reset LOCAL public schema?" || exit 4
  if (( APPLY == 1 )); then reset_public "$PRIMARY_DSN" "local"; else log "[plan] would RESET local"; fi
fi
if (( RESET_REMOTE == 1 )) && [[ -n "$REMOTE_DSN" ]]; then
  confirm "Reset REMOTE public schema?" || exit 4
  if (( APPLY == 1 )); then reset_public "$REMOTE_DSN" "remote"; else log "[plan] would RESET remote"; fi
fi

apply_group() {
  local label="$1"; shift; local arr=("$@")
  for f in "${arr[@]}"; do
    [[ -z "$f" ]] && continue
    # Apply to remote first if present, then primary (mirroring earlier simple scripts that were remote-focused)
    if [[ -n "$REMOTE_DSN" ]]; then apply_file "$f" "$REMOTE_DSN" "remote"; fi
    if [[ -n "$PRIMARY_DSN" ]]; then apply_file "$f" "$PRIMARY_DSN" "primary"; fi
  done
}

apply_group base "${FILES_BASE[@]}"
apply_group indexes "${FILES_INDEXES[@]}"
apply_group security "${FILES_SECURITY[@]}"

if (( APPLY == 0 )); then
  log "Dry run complete. Re-run with --apply to execute."
else
  log "Full sync complete."
fi

exit 0
