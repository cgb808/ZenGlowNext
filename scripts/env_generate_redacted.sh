#!/usr/bin/env bash
set -euo pipefail
# Generate a redacted copy of .env at .env.redacted (values hidden or partially masked)
# Does NOT modify the original .env.
# Usage: bash scripts/env_generate_redacted.sh

SRC_FILE=".env"
OUT_FILE=".env.redacted"

[[ -f $SRC_FILE ]] || { echo "[error] $SRC_FILE not found" >&2; exit 1; }

echo "[info] Generating $OUT_FILE from $SRC_FILE" >&2
awk 'BEGIN{FS="="; OFS="="}
/^[A-Za-z0-9_]+=/ {
  key=$1; val=$2; for(i=3;i<=NF;i++){val=val"="$(i)}
  if (val ~ /^\*\*\*MASKED\*\*\*/){ print $0; next }
  if(length(val)>10){print key,"***MASKED:"substr(val,1,6)"***"}
  else if(length(val)>0){print key,"***MASKED***"}
  else {print key"="}
  next
}
{print $0}' "$SRC_FILE" > "$OUT_FILE"

echo "[ok] Wrote $OUT_FILE (safe to open/share internally)." >&2
