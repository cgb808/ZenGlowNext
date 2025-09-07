#!/usr/bin/env bash
set -euo pipefail
###############################################
# vault_env_sync.sh
# Manage .env secrets against Vault KV v2 (pull / push / diff / prune / export / import)
###############################################
# Requirements:
#  - vault CLI logged in (VAULT_TOKEN exported or active session).
#  - VAULT_ADDR set. Either set VAULT_SECRETS_PATH (full kv/data/<path>) OR provide
#    VAULT_KV_MOUNT + VAULT_KV_PATH and script will build VAULT_SECRETS_PATH.
#  - Optional VAULT_NAMESPACE for HCP / Enterprise namespaces.
#
# Subcommands:
#   pull              : Merge Vault -> .env (backs up existing to .env.bak.TIMESTAMP)
#   push              : Patch Vault with non-empty local keys (supports PUSH_KEYS filter, DRY_RUN=1)
#   list              : List keys currently stored in Vault
#   diff              : Show differences (added/changed/removed) between local .env and Vault
#   prune             : Remove keys from Vault that are NOT present locally (requires PRUNE_CONFIRM=YES)
#   export-json       : Print JSON of Vault data to stdout
#   import-json FILE  : Patch Vault with key/values from a JSON file containing flat object or {data:{...}}
#
# Environment knobs:
#   DRY_RUN=1               : Dry-run mode for push/prune/import
#   PUSH_KEYS="K1,K2"        : Only push listed keys (comma or space separated)
#   SHOW_VALUES=1           : For list/diff, display full secret values (DANGEROUS)
#   MASK_PREFIX_LEN=4       : Masking prefix length (default 6 if unset)
#   PRUNE_CONFIRM=YES       : Required to actually prune
#
# Notes:
#  - Only KEY=VALUE lines (non-empty VALUE) are considered for push/import.
#  - Comments / blank lines ignored.
#  - Diff does not display full values unless SHOW_VALUES=1 (shows hash + prefix instead).
###############################################

MODE=${1:-}
ARG2=${2:-}
ENV_FILE=".env"
MASK_PREFIX_LEN=${MASK_PREFIX_LEN:-6}

: "${VAULT_ADDR?VAULT_ADDR not set}"

# Allow dynamic build of VAULT_SECRETS_PATH if not supplied but mount & path provided
if [[ -z "${VAULT_SECRETS_PATH:-}" ]]; then
  if [[ -n "${VAULT_KV_MOUNT:-}" && -n "${VAULT_KV_PATH:-}" ]]; then
    # KV v2 data path format: <mount>/data/<path>
    VAULT_SECRETS_PATH="${VAULT_KV_MOUNT%/}/data/${VAULT_KV_PATH#./}"
  else
    echo "[error] Provide VAULT_SECRETS_PATH or VAULT_KV_MOUNT + VAULT_KV_PATH" >&2; exit 1
  fi
fi

if ! command -v vault >/dev/null 2>&1; then
  echo "[error] vault CLI not found in PATH" >&2
  exit 2
fi

if [[ -n "${VAULT_NAMESPACE:-}" ]]; then
  export VAULT_NAMESPACE
fi

kv_read() { vault kv get -format=json "$VAULT_SECRETS_PATH" 2>/dev/null || true; }

kv_read_flat() {
  local raw=$(kv_read); [[ -z $raw ]] && return 0
  if command -v jq >/dev/null 2>&1; then
    jq -r '.data.data | to_entries[] | "\(.key)=\(.value)"' <<<"$raw"
  else
    echo "$raw" | sed -n 's/.*"data":{"data":{\(.*\)}.*/\1/p' | tr ',' '\n' | sed 's/"//g' | sed 's/:/=/g'
  fi
}

kv_write() {
  # Accepts key=value pairs as args; builds JSON for patch
  local json="{\"data\":{"
  local first=1
  for kv in "$@"; do
    local k="${kv%%=*}"; local v="${kv#*=}";
    [[ -z $k ]] && continue
    if (( first )); then first=0; else json+=","; fi
    # Escape quotes
    v_esc=$(printf '%s' "$v" | sed 's/"/\\"/g')
    json+="\"$k\":\"$v_esc\""
  done
  json+="}}"
  echo "$json" | vault kv patch "$VAULT_SECRETS_PATH" - >/dev/null
}

backup_env() {
  [[ -f $ENV_FILE ]] || return 0
  cp "$ENV_FILE" ".env.bak.$(date +%Y%m%d-%H%M%S)"
}

mask_val() {
  local v="$1"; local pre=${v:0:$MASK_PREFIX_LEN}
  if [[ -n "${SHOW_VALUES:-}" ]]; then
    printf '%s' "$v"
  else
    printf '%s***' "$pre"
  fi
}

hash_val() { printf '%s' "$1" | sha256sum 2>/dev/null | awk '{print $1}' || shasum -a 256 | awk '{print $1}'; }

pull_env() {
  echo "[info] Pulling secrets from Vault -> $ENV_FILE"
  local raw json keys
  raw=$(kv_read)
  if [[ -z $raw ]]; then
    echo "[warn] No existing data at $VAULT_SECRETS_PATH (or access denied)" >&2
    return 1
  fi
  backup_env
  # Extract key/value pairs
  kv_read_flat > .env.vault.tmp
  # Merge strategy: overwrite existing keys, preserve others
  declare -A newmap
  while IFS='=' read -r k v; do
    [[ -z $k || $k =~ ^# ]] && continue
    newmap[$k]="$v"
  done < .env.vault.tmp
  rm .env.vault.tmp
  # Rebuild .env
  if [[ -f $ENV_FILE ]]; then
    awk -v OFS='=' -v RS='\n' -v ORS='\n' -v mapfile="/dev/stdin" 'BEGIN{while((getline line < mapfile)>0){split(line,a,"="); data[a[1]]=substr(line,length(a[1])+2)}}
      /^[A-Za-z0-9_]+=/ {key=$1; sub(/=.*/,"",key); base=$0; split($0,a,"="); k=a[1]; if(k in data){print k"="data[k]; delete data[k]} else {print}} 
      /^[^A-Za-z0-9_]/ {print} 
      END{for(k in data) print k"="data[k]}' <(for k in "${!newmap[@]}"; do echo "$k=${newmap[$k]}"; done) "$ENV_FILE" > .env.new
  else
    for k in "${!newmap[@]}"; do echo "$k=${newmap[$k]}"; done > .env.new
  fi
  mv .env.new "$ENV_FILE"
  echo "[ok] Pull complete. Backup(s) preserved with .env.bak.*"
}

push_env() {
  echo "[info] Pushing populated keys from $ENV_FILE -> Vault path $VAULT_SECRETS_PATH"
  [[ -f $ENV_FILE ]] || { echo "[error] $ENV_FILE not found" >&2; exit 1; }
  mapfile -t pairs < <(grep -E '^[A-Za-z0-9_]+=' "$ENV_FILE" | grep -v '^#' | while IFS='=' read -r k v; do [[ -n $v ]] && echo "$k=$v"; done )
  if [[ -n "${PUSH_KEYS:-}" ]]; then
    # Normalize separators
    IFS=', ' read -r -a filter <<< "$PUSH_KEYS"
    declare -A want
    for f in "${filter[@]}"; do [[ -n $f ]] && want[$f]=1; done
    tmp=()
    for kv in "${pairs[@]}"; do k="${kv%%=*}"; [[ ${want[$k]:-} ]] && tmp+=("$kv"); done
    pairs=(${tmp[@]:-})
  fi
  if (( ${#pairs[@]} == 0 )); then
    echo "[warn] No non-empty key=value pairs to push" >&2
    return 1
  fi
  if [[ "${DRY_RUN:-}" == 1 ]]; then
    echo "[dry-run] Would push:"
    printf '  %s\n' "${pairs[@]}"
    return 0
  fi
  kv_write "${pairs[@]}"
  echo "[ok] Push complete (patched existing secret)."
}

list_env() {
  echo "[info] Listing Vault secrets at $VAULT_SECRETS_PATH"
  raw=$(kv_read)
  if [[ -z $raw ]]; then echo "[warn] None"; return 0; fi
  if command -v jq >/dev/null 2>&1; then
    jq -r '.data.data | to_entries[] | "- \(.key)"' <<<"$raw"
  else
    echo "$raw" | sed -n 's/.*"data":{"data":{\(.*\)}.*/\1/p' | tr ',' '\n' | sed 's/"//g' | cut -d: -f1 | sed 's/^/- /'
  fi
}

diff_env() {
  echo "[info] Diff local .env vs Vault"
  declare -A vault localmap
  while IFS='=' read -r k v; do [[ -z $k ]] && continue; vault[$k]="$v"; done < <(kv_read_flat || true)
  while IFS='=' read -r k v; do [[ -z $k || $k =~ ^# ]] && continue; localmap[$k]="$v"; done < <(grep -E '^[A-Za-z0-9_]+=' "$ENV_FILE" | grep -v '^#')
  # Collect union keys
  declare -A seen
  for k in "${!vault[@]}"; do seen[$k]=1; done
  for k in "${!localmap[@]}"; do seen[$k]=1; done
  for k in $(printf '%s\n' "${!seen[@]}" | sort); do
    v_v="${vault[$k]-}"; v_l="${localmap[$k]-}"
    if [[ -n "$v_v" && -n "$v_l" ]]; then
      if [[ "$v_v" == "$v_l" ]]; then
        echo "= $k=$(mask_val "$v_l")"
      else
        echo "~ $k local=$(mask_val "$v_l") vault=$(mask_val "$v_v") hash_local=$(hash_val "$v_l") hash_vault=$(hash_val "$v_v")"
      fi
    elif [[ -n "$v_l" ]]; then
      echo "+ $k=$(mask_val "$v_l")"
    else
      echo "- $k=$(mask_val "$v_v")"
    fi
  done
}

prune_env() {
  echo "[warn] Prune will DELETE Vault keys not present locally" >&2
  [[ "${PRUNE_CONFIRM:-}" == "YES" ]] || { echo "[abort] Set PRUNE_CONFIRM=YES to proceed" >&2; return 2; }
  # Build key set
  declare -A localmap
  while IFS='=' read -r k v; do [[ -z $k || $k =~ ^# ]] && continue; localmap[$k]=1; done < <(grep -E '^[A-Za-z0-9_]+=' "$ENV_FILE" | grep -v '^#')
  mapfile -t to_delete < <(kv_read_flat | cut -d= -f1 | while read -r k; do [[ -z ${localmap[$k]:-} ]] && echo "$k"; done)
  if (( ${#to_delete[@]} == 0 )); then echo "[info] Nothing to prune"; return 0; fi
  echo "[info] Keys to delete: ${to_delete[*]}"
  if [[ "${DRY_RUN:-}" == 1 ]]; then echo "[dry-run] Skipping delete"; return 0; fi
  # Need mount & path for delete operations; derive data path to metadata path
  # VAULT_SECRETS_PATH = <mount>/data/<path>
  mount_part="${VAULT_SECRETS_PATH%%/data/*}"; rest="${VAULT_SECRETS_PATH#*/data/}";
  for k in "${to_delete[@]}"; do
    echo "[del] $k"
    vault kv patch "$VAULT_SECRETS_PATH" -<<JSON >/dev/null
{"data": {"$k": null}}
JSON
  done
  echo "[ok] Prune complete"
}

export_json() { kv_read | jq -r '.data.data' 2>/dev/null || kv_read; }

import_json() {
  local file="$ARG2"; [[ -f $file ]] || { echo "[error] File $file not found" >&2; return 1; }
  if ! command -v jq >/dev/null 2>&1; then echo "[error] jq required for import-json" >&2; return 2; fi
  # Accept either a flat object or object with .data/.data.data structure
  local payload=$(jq -c 'if has("data") and .data|type=="object" then .data else . end | if has("data") and .data|type=="object" then .data else . end' "$file")
  # Convert to key=value list
  mapfile -t pairs < <(jq -r 'to_entries[] | "\(.key)=\(.value)"' <<<"$payload")
  if (( ${#pairs[@]} == 0 )); then echo "[warn] No keys in JSON" >&2; return 1; fi
  if [[ "${DRY_RUN:-}" == 1 ]]; then echo "[dry-run] Would import: ${pairs[*]}"; return 0; fi
  kv_write "${pairs[@]}"
  echo "[ok] Import complete"
}

usage() {
  grep '^# ' "$0" | sed 's/^# \{0,1\}//'
}

case "$MODE" in
  pull) pull_env ;;
  push) push_env ;;
  list) list_env ;;
  diff) diff_env ;;
  prune) prune_env ;;
  export-json) export_json ;;
  import-json) import_json ;;
  help|--help|-h|'') usage ;;
  *) echo "[error] Unknown command: $MODE" >&2; usage >&2; exit 1 ;;
esac
