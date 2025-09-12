#!/usr/bin/env bash
set -euo pipefail

# collect_secrets.sh
# Interactive (or non-interactive via env) secret gathering helper.
# Does NOT apply schema or push migrations. Only gathers and (optionally) stores secrets.
# If --export-env is provided, prints export lines to stdout for copy/paste.
# If --supabase set is provided with --project-ref, can store selected keys via `supabase secrets set`.
# (Requires Supabase CLI auth for remote secret storage.)
#
# Supported secrets (toggle with flags or default all):
#   POSTGRES_PASSWORD, JWT_SECRET, SUPABASE_SERVICE_KEY (input only), SUPABASE_ANON_KEY (input only),
#   REDIS_PASSWORD (optional), GATE_TOKEN (optional)
#
# Generation: Strong random values (base64url) for POSTGRES_PASSWORD, JWT_SECRET, REDIS_PASSWORD, GATE_TOKEN if not supplied.
#
# Usage examples:
#   ./scripts/collect_secrets.sh --export-env
#   ./scripts/collect_secrets.sh --project-ref fwduxnqlraijxlprxsjy --supabase-set POSTGRES_PASSWORD JWT_SECRET
#   POSTGRES_PASSWORD=provided ./scripts/collect_secrets.sh --export-env
#
# Exit codes: 0 success | 2 arg error | 3 missing supabase when requested

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 3; }; }
rand_b64url() { # length param (bytes) default 32
  local n=${1:-32}
  openssl rand -base64 $n | tr '+/' '-_' | tr -d '=' | cut -c1-$((n*4/3))
}
prompt_secret() {
  local var=$1; local msg=$2; local genlen=${3:-32}; local current=${!var-}
  if [[ -n "$current" ]]; then
    echo "$var (provided via env)"; return 0; fi
  read -r -p "$msg (leave blank to auto-generate): " input || true
  if [[ -z "$input" ]]; then
    export "$var"="$(rand_b64url "$genlen")"
    echo "$var= (generated)";
  else
    export "$var"="$input"; echo "$var= (entered)";
  fi
}

EXPORT_ENV=0
SUPABASE_SET=()
PROJECT_REF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --export-env) EXPORT_ENV=1; shift ;;
    --supabase-set) shift; while [[ $# -gt 0 && $1 != --* ]]; do SUPABASE_SET+=("$1"); shift; done ;;
    --project-ref) PROJECT_REF="$2"; shift 2 ;;
    -h|--help) sed -n '1,/^need_cmd/p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Collect core secrets
prompt_secret POSTGRES_PASSWORD "Enter Postgres password" 24
prompt_secret JWT_SECRET "Enter JWT secret (>=32 chars recommended)" 48
prompt_secret REDIS_PASSWORD "Enter Redis password" 24
prompt_secret GATE_TOKEN "Enter Gate token" 32

# Non-generated (user must paste if desired)
if [[ -z ${SUPABASE_SERVICE_KEY-} ]]; then read -r -p "Paste SUPABASE_SERVICE_KEY (optional, ENTER to skip): " SUPABASE_SERVICE_KEY || true; fi
if [[ -z ${SUPABASE_ANON_KEY-} ]]; then read -r -p "Paste SUPABASE_ANON_KEY (optional, ENTER to skip): " SUPABASE_ANON_KEY || true; fi

# Export lines
if (( EXPORT_ENV == 1 )); then
  echo "# Copy these into your .env (do not commit secrets)" >&2
  cat <<EOF
export POSTGRES_PASSWORD="$POSTGRES_PASSWORD"
export JWT_SECRET="$JWT_SECRET"
export REDIS_PASSWORD="$REDIS_PASSWORD"
export GATE_TOKEN="$GATE_TOKEN"
${SUPABASE_SERVICE_KEY:+export SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY"}
${SUPABASE_ANON_KEY:+export SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY"}
EOF
fi

# Supabase secrets set
if ((${#SUPABASE_SET[@]} > 0)); then
  need_cmd supabase
  if [[ -z "$PROJECT_REF" ]]; then
    echo "--project-ref required with --supabase-set" >&2; exit 2
  fi
  # Build key=value args (only for those collected)
  declare -A map
  map[POSTGRES_PASSWORD]="$POSTGRES_PASSWORD"
  map[JWT_SECRET]="$JWT_SECRET"
  map[REDIS_PASSWORD]="$REDIS_PASSWORD"
  map[GATE_TOKEN]="$GATE_TOKEN"
  map[SUPABASE_SERVICE_KEY]="$SUPABASE_SERVICE_KEY"
  map[SUPABASE_ANON_KEY]="$SUPABASE_ANON_KEY"
  to_set=()
  for k in "${SUPABASE_SET[@]}"; do
    v=${map[$k]:-}
    if [[ -n "$v" ]]; then
      to_set+=("$k=$v")
    else
      echo "Skip $k (empty)" >&2
    fi
  done
  if ((${#to_set[@]} > 0)); then
    echo "Setting secrets remotely: ${to_set[*]}" >&2
    supabase secrets set "${to_set[@]}" --project-ref "$PROJECT_REF"
  else
    echo "No secrets to set remotely." >&2
  fi
fi

echo "Secret collection complete."
