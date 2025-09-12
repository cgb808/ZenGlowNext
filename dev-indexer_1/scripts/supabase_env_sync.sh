#!/usr/bin/env bash
set -euo pipefail

# supabase_env_sync.sh
# Unified helper to consolidate Supabase + local secret env handling and run schema verifiers.
#
# Features:
#   - Merge supplied key=value pairs or an input env file into a target .env (non‑destructive by default).
#   - Optionally pull remote secrets from a Supabase table via fetch_supabase_secrets.sh.
#   - Validate presence of critical Supabase variables (project ref / service key / URL or DB URL).
#   - Run connectivity probe (simple SELECT 1) using either Supabase CLI (db query) or psql.
#   - Optionally invoke metrics and dev KG verification scripts (plan or execute).
#   - Dry run mode prints planned actions without modifying files.
#
# Usage examples:
#   # Merge local kv pairs into .env (adds only missing keys)
#   ./scripts/supabase_env_sync.sh --target .env \
#       --set SUPABASE_PROJECT_REF=abcd1234 SUPABASE_URL=https://abcd.supabase.co \
#       --set SUPABASE_SERVICE_KEY=service... --validate --plan-only
#
#   # Pull remote secrets then run both verifiers (execute, not plan)
#   SUPABASE_URL=https://abcd.supabase.co SUPABASE_SERVICE_KEY=service... \
#     ./scripts/supabase_env_sync.sh --target .env --pull-remote-secrets \
#       --run-metrics --run-kg --validate
#
#   # Just refresh remote secrets into .env and show SQL only for metrics
#   ./scripts/supabase_env_sync.sh --pull-remote-secrets --run-metrics --metrics-plan --target .env
#
# Flags:
#   --target FILE            Target env file (default .env)
#   --set KEY=VAL [...]      Inline key=value pairs to merge (may repeat)
#   --from FILE              Additional env file to merge (dotenv style)
#   --pull-remote-secrets    Use fetch_supabase_secrets.sh to fetch and merge secrets
#   --secrets-table NAME     Override secrets table (default app_secrets)
#   --overwrite              Overwrite existing keys instead of keeping originals
#   --validate               Enforce required vars (project ref / keys / URL) after merge
#   --plan-only              Show intended changes; do not modify target or run verifiers
#   --probe-db               Perform connectivity probe (SELECT 1)
#   --run-metrics            Run metrics_schema_verify.sh (executes unless --metrics-plan)
#   --metrics-plan           Pass --plan to metrics verifier (print SQL only)
#   --future-days N          Forward to metrics verifier (partition ensure)
#   --hourly-today           Forward to metrics verifier
#   --run-kg                 Run dev_kg_schema_verify.sh (executes unless --kg-plan)
#   --kg-plan                Pass --plan to KG verifier
#   --dry-run                Alias for --plan-only (deprecated name)
#   --show-full              Disable masking of sensitive values in plan output
#   -h|--help                Help output
#
# Required (when validating / running verifiers):
#   SUPABASE_PROJECT_REF (unless using SUPABASE_DB_URL directly with psql fallback)
#   SUPABASE_SERVICE_KEY (for remote secrets + potential future auth use)
#   SUPABASE_URL (for remote secrets) and/or SUPABASE_DB_URL (direct DSN)
#
# Exit codes:
#   0 success | 2 arg error | 3 validation failure | 4 probe failure | 5 verifier failure

TARGET=".env"
INLINES=()
FROM_FILE=""
PULL_REMOTE=0
SECRETS_TABLE="app_secrets"
OVERWRITE=0
VALIDATE=0
PLAN_ONLY=0
PROBE=0
RUN_METRICS=0
METRICS_PLAN=0
FUTURE_DAYS=""
HOURLY_TODAY=0
RUN_KG=0
KG_PLAN=0
SHOW_FULL=0

usage() { sed -n '1,/^Exit codes:/p' "$0"; } 2>/dev/null || true

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --set) INLINES+=("$2"); shift 2 ;;
    --from) FROM_FILE="$2"; shift 2 ;;
    --pull-remote-secrets) PULL_REMOTE=1; shift ;;
    --secrets-table) SECRETS_TABLE="$2"; shift 2 ;;
    --overwrite) OVERWRITE=1; shift ;;
    --validate) VALIDATE=1; shift ;;
    --plan-only|--dry-run) PLAN_ONLY=1; shift ;;
    --probe-db) PROBE=1; shift ;;
    --run-metrics) RUN_METRICS=1; shift ;;
    --metrics-plan) METRICS_PLAN=1; shift ;;
    --future-days) FUTURE_DAYS="$2"; shift 2 ;;
    --hourly-today) HOURLY_TODAY=1; shift ;;
    --run-kg) RUN_KG=1; shift ;;
    --kg-plan) KG_PLAN=1; shift ;;
  --show-full) SHOW_FULL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

declare -A MERGE

load_from_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ $line == *"="* ]]; then
      local k=${line%%=*}
      local v=${line#*=}
      MERGE["$k"]="$v"
    fi
  done < "$f"
}

# Start with existing target (so we can skip overwriting unless allowed)
if [[ -f "$TARGET" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* || $line != *"="* ]] && continue
    k=${line%%=*}
    v=${line#*=}
    MERGE["$k"]="$v"
  done < "$TARGET"
fi

[[ -n "$FROM_FILE" ]] && load_from_file "$FROM_FILE"

# Inline key=val pairs
for kv in "${INLINES[@]}"; do
  if [[ $kv != *"="* ]]; then
    echo "--set expects KEY=VAL got '$kv'" >&2; exit 2
  fi
  k=${kv%%=*}; v=${kv#*=}
  if [[ $OVERWRITE -eq 1 || -z ${MERGE[$k]+_} ]]; then
    MERGE["$k"]="$v"
  fi
done

# Remote secrets
if (( PULL_REMOTE )); then
  : "${SUPABASE_URL:?SUPABASE_URL required for remote secrets}"
  : "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY required for remote secrets}"
  tmpfile=$(mktemp)
  SECRETS_TABLE=$SECRETS_TABLE OUTPUT_FILE="$tmpfile" \
    bash "$(dirname "$0")/fetch_supabase_secrets.sh" >/dev/null
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* || $line != *"="* ]] && continue
    k=${line%%=*}; v=${line#*=}
    if [[ $OVERWRITE -eq 1 || -z ${MERGE[$k]+_} ]]; then
      MERGE["$k"]="$v"
    fi
  done < "$tmpfile"
  rm -f "$tmpfile"
fi

required_vars=(SUPABASE_SERVICE_KEY SUPABASE_PROJECT_REF SUPABASE_URL SUPABASE_ANON_KEY)

if (( VALIDATE )); then
  missing=()
  for rv in "${required_vars[@]}"; do
    if [[ -z ${MERGE[$rv]:-} ]]; then
      missing+=("$rv")
    fi
  done
  if ((${#missing[@]} > 0)); then
    echo "Missing required vars: ${missing[*]}" >&2
    exit 3
  fi
fi

if (( PLAN_ONLY )); then
  echo "--- PLAN (no changes) ---"
  echo "Target: $TARGET"; echo "Overwrite: $OVERWRITE"; echo "Keys after merge:";
  mask() {
    local key="$1" val="$2"
    if (( SHOW_FULL )); then
      printf '%s' "$val"; return
    fi
    # Keys considered sensitive (substring match, case insensitive)
    if [[ "$key" =~ (?i)(KEY|SECRET|TOKEN|PASSWORD|PASS|JWT) ]]; then
      # Preserve length + last 4 chars if length > 12
      local len=${#val}
      if (( len <= 8 )); then
        printf '******'
      else
        local tail=${val: -4}
        local stars=$(( len-4 ))
        printf '%*s%s' "$stars" '' "$tail" | tr ' ' '*'
      fi
    else
      # For URLs containing secrets (very naive), hide query value(s)
      if [[ "$val" == *"://"* ]]; then
        printf '%s' "$val" | sed -E 's#(://[^:@]+:)[^@]+@#\1***@#'
      else
        printf '%s' "$val"
      fi
    fi
  }
  for k in "${!MERGE[@]}"; do
    echo "  $k=$(mask "$k" "${MERGE[$k]}")"
  done | sort
else
  {
    echo "# Updated by supabase_env_sync.sh $(date -Iseconds)";
    for k in "${!MERGE[@]}"; do
      echo "$k=${MERGE[$k]}"
    done | sort
  } > "$TARGET.tmp"
  mv "$TARGET.tmp" "$TARGET"
  echo "Wrote $TARGET (${#MERGE[@]} keys)"
fi

probe_with_supabase() {
  local sql="SELECT 1 as ok;"
  supabase db query <<<"$sql" >/dev/null 2>&1
}

probe_with_psql() {
  local dsn="$1"; local sql="SELECT 1;"
  PGPASSWORD="${PGPASSWORD:-}" psql "$dsn" -c "$sql" -q >/dev/null
}

if (( PROBE )); then
  if (( PLAN_ONLY )); then
    echo "(skip probe due to plan-only)"
  else
    echo "Probing database connectivity..."
    HAS_SUPA=0
    if command -v supabase >/dev/null 2>&1 && supabase db --help 2>/dev/null | grep -q query; then
      if probe_with_supabase; then
        echo "Supabase CLI probe ok"; HAS_SUPA=1
      fi
    fi
    if (( HAS_SUPA == 0 )); then
      DSN="${SUPABASE_DB_URL:-${DATABASE_URL:-}}"
      if [[ -z "$DSN" ]]; then
        echo "No DSN for psql probe (need SUPABASE_DB_URL or DATABASE_URL)" >&2; exit 4
      fi
      if probe_with_psql "$DSN"; then
        echo "psql probe ok"
      else
        echo "psql probe failed" >&2; exit 4
      fi
    fi
  fi
fi

run_metrics() {
  local args=()
  if [[ -n ${MERGE[SUPABASE_PROJECT_REF]:-} ]]; then
    args+=(--project-ref "${MERGE[SUPABASE_PROJECT_REF]}")
  fi
  if [[ -n "$FUTURE_DAYS" ]]; then args+=(--future-days "$FUTURE_DAYS"); fi
  if (( HOURLY_TODAY )); then args+=(--hourly-today); fi
  if (( METRICS_PLAN )); then args+=(--plan); fi
  bash "$(dirname "$0")/metrics_schema_verify.sh" "${args[@]}"
}

run_kg() {
  local args=()
  if [[ -n ${MERGE[SUPABASE_PROJECT_REF]:-} ]]; then
    args+=(--project-ref "${MERGE[SUPABASE_PROJECT_REF]}")
  fi
  if (( KG_PLAN )); then args+=(--plan); fi
  bash "$(dirname "$0")/dev_kg_schema_verify.sh" "${args[@]}"
}

if (( RUN_METRICS )); then
  if (( PLAN_ONLY )); then
    echo "(skip metrics verifier due to plan-only)"
  else
    echo "Running metrics verifier..."
    if ! run_metrics; then echo "Metrics verifier failed" >&2; exit 5; fi
  fi
fi

if (( RUN_KG )); then
  if (( PLAN_ONLY )); then
    echo "(skip KG verifier due to plan-only)"
  else
    echo "Running KG verifier..."
    if ! run_kg; then echo "KG verifier failed" >&2; exit 5; fi
  fi
fi

echo "supabase_env_sync complete."
