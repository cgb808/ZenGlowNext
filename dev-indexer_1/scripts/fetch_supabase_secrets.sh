#!/usr/bin/env bash
set -euo pipefail

# fetch_supabase_secrets.sh
# Purpose: Pull key/value secrets from a Supabase table (app_secrets) and export
# them into an env file or directly evaluate them in the current shell.
#
# Requirements:
#   - SUPABASE_URL (base project URL, e.g. https://xxx.supabase.co)
#   - SUPABASE_SERVICE_KEY (service role key for full RLS bypass)
#   - (Optional) SECRETS_TABLE (default: app_secrets)
#   - (Optional) OUTPUT_FILE (default: .supabase.secrets.env)
#
# Table schema expectation:
#   create table if not exists app_secrets (
#     key text primary key,
#     value text not null,
#     updated_at timestamptz default now()
#   );
# Insert secrets:
#   insert into app_secrets (key,value) values ('JWT_SECRET','super-secret'), ('SUPABASE_ANON_KEY','...');
#
# Usage:
#   ./scripts/fetch_supabase_secrets.sh              # writes OUTPUT_FILE
#   eval $(./scripts/fetch_supabase_secrets.sh --print-export)  # export into shell
#   ./scripts/fetch_supabase_secrets.sh --sync-to .env           # merge into .env (non-destructive)
#
# Notes:
#   - Avoid committing OUTPUT_FILE.
#   - Service key is powerful: guard it (do NOT bake into images).

SECRETS_TABLE=${SECRETS_TABLE:-app_secrets}
OUTPUT_FILE=${OUTPUT_FILE:-.supabase.secrets.env}
MODE="file"  # file|print|sync
SYNC_TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --print-export)
      MODE="print"; shift ;;
    --sync-to)
      MODE="sync"; SYNC_TARGET="$2"; shift 2 ;;
    --table)
      SECRETS_TABLE="$2"; shift 2 ;;
    --output)
      OUTPUT_FILE="$2"; shift 2 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# //'; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

: "${SUPABASE_URL:?SUPABASE_URL required}"
: "${SUPABASE_SERVICE_KEY:?SUPABASE_SERVICE_KEY required}"

API="$SUPABASE_URL/rest/v1/$SECRETS_TABLE?select=key,value"
JSON=$(curl -sS -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" "$API")
if [[ -z "$JSON" || "$JSON" == "[]" ]]; then
  echo "No secrets returned (table empty or RLS blocking)." >&2
  exit 1
fi

# Parse with jq if available, else use awk fallback (assumes simple JSON array)
if command -v jq >/dev/null 2>&1; then
  mapfile -t LINES < <(echo "$JSON" | jq -r '.[] | "\(.key)=\(.value)"')
else
  # very naive: key/value must not contain embedded quotes or commas
  LINES=()
  while IFS= read -r line; do
    if [[ $line =~ "key" ]]; then
      k=$(echo "$line" | sed -E 's/.*"key" *: *"([^"]+)".*/\1/')
    fi
    if [[ $line =~ "value" ]]; then
      v=$(echo "$line" | sed -E 's/.*"value" *: *"([^"]+)".*/\1/')
      if [[ -n "$k" ]]; then
        LINES+=("$k=$v")
        k=""; v=""
      fi
    fi
  done < <(echo "$JSON" | tr '{' '\n')
fi

case "$MODE" in
  file)
    {
      echo "# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) from $SECRETS_TABLE"
      for kv in "${LINES[@]}"; do
        echo "$kv"
      done
    } > "$OUTPUT_FILE"
    echo "Wrote $OUTPUT_FILE (${#LINES[@]} secrets)." ;;
  print)
    for kv in "${LINES[@]}"; do
      # shellcheck disable=SC2016
      echo "export $kv"
    done ;;
  sync)
    : "${SYNC_TARGET:?--sync-to requires a target file}";
    touch "$SYNC_TARGET"
    # Merge only keys not already present
    for kv in "${LINES[@]}"; do
      key=${kv%%=*}
      if ! grep -Eq "^${key}=" "$SYNC_TARGET"; then
        echo "$kv" >> "$SYNC_TARGET"
      fi
    done
    echo "Synced new secrets into $SYNC_TARGET" ;;
  *) echo "Unknown mode $MODE" >&2; exit 1 ;;
 esac
