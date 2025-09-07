#!/usr/bin/env bash
set -euo pipefail
# Generate a minimal ingestion/shared env file for the Zendexer Copilot repo.
# Pulls whitelisted variables from the main .env and writes .env.zendexer (masked optional).
# Usage: bash scripts/env_generate_zendexer_readonly.sh [--mask]

SRC_FILE=.env
OUT_FILE=.env.zendexer
MASK=0
if [[ "${1:-}" == "--mask" ]]; then MASK=1; fi

[[ -f $SRC_FILE ]] || { echo "[error] $SRC_FILE not found" >&2; exit 1; }

# Whitelist of keys to export (extend as needed)
WHITELIST=( \
  SUPABASE_URL \
  SUPABASE_ANON_KEY \
  SUPABASE_PROJECT_REF \
  RAG_SEARCH_FUNCTION \
  RAG_CHUNK_SEARCH_FUNCTION \
  RAG_TOP_K \
  RAG_MIN_SCORE \
  LLM_FUNCTION_PATH \
  ZENDEXER_INGEST_KEY \
)

: > "$OUT_FILE"
while IFS='=' read -r k v; do
  [[ -z "$k" || "$k" =~ ^# ]] && continue
  if printf '%s\n' "${WHITELIST[@]}" | grep -qx "$k"; then
    if [[ $MASK -eq 1 && -n "$v" ]]; then
      if [[ ${#v} -gt 10 ]]; then
        echo "$k=***MASKED:${v:0:6}***" >> "$OUT_FILE"
      else
        echo "$k=***MASKED***" >> "$OUT_FILE"
      fi
    else
      echo "$k=$v" >> "$OUT_FILE"
    fi
  fi
done < "$SRC_FILE"

echo "[ok] Wrote $OUT_FILE (mask=$MASK)" >&2
