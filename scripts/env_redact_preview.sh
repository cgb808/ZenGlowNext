#!/usr/bin/env bash
set -euo pipefail
# Show .env with values partially redacted (keep first 6 chars) for review/logging.
file=".env"
[[ -f $file ]] || { echo "[error] .env not found" >&2; exit 1; }
awk 'BEGIN{FS="="; OFS="="}
/^[A-Za-z0-9_]+=/ {
  key=$1; val=$2; for(i=3;i<=NF;i++){val=val"="$(i)}
  if(length(val)>10){print key, substr(val,1,6)"***REDACTED***"}
  else if(length(val)>0){print key, "***REDACTED***"}
  else {print $0}
  next
}
{print $0}' "$file"
