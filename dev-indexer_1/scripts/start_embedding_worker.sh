#!/usr/bin/env bash
set -euo pipefail

# Deliberate staged startup for embedding worker (low churn environment)
# Waits longer between dependency checks to ensure services are fully warm.
# Configurable via environment variables:
#   STARTUP_WAIT_DB=seconds (default 30)
#   STARTUP_WAIT_APP=seconds (default 30)
#   STARTUP_WAIT_EMBED=seconds (default 45)
#   EXTRA_SLEEP_AFTER=seconds (default 20)
#   MAX_RETRIES=integer (default 20)
#   APP_HEALTH_URL (default http://app:8000/health)
#   EMBED_HEALTH_URL (optional – skip if unset)
#   DATABASE_URL (required for worker)
#   BATCH_SIZE / POLL_INTERVAL etc passed through
#
# Usage (Compose service command):
#   scripts/start_embedding_worker.sh
#
# This script launches: python app/inference/gating.py --db-url "$DATABASE_URL"

APP_HEALTH_URL=${APP_HEALTH_URL:-http://app:8000/health}
EMBED_HEALTH_URL=${EMBED_HEALTH_URL:-}
STARTUP_WAIT_DB=${STARTUP_WAIT_DB:-30}
STARTUP_WAIT_APP=${STARTUP_WAIT_APP:-30}
STARTUP_WAIT_EMBED=${STARTUP_WAIT_EMBED:-45}
EXTRA_SLEEP_AFTER=${EXTRA_SLEEP_AFTER:-20}
MAX_RETRIES=${MAX_RETRIES:-20}

log() { echo "[start-embed-worker] $*"; }

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing dependency: $1" >&2; exit 2; }; }
need curl

[ -n "${DATABASE_URL:-}" ] || { echo "DATABASE_URL required" >&2; exit 2; }

retry_wait() { # url delay label
  local url=$1 delay=$2 label=$3 attempt=0
  while (( attempt < MAX_RETRIES )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$label ready (attempt $attempt)"
      return 0
    fi
    log "wait($label) attempt=$attempt sleeping $delay s: $url"
    sleep "$delay"
    attempt=$((attempt+1))
  done
  echo "timeout waiting for $label: $url" >&2
  return 1
}

# Stage 1: give DB time (even if health not exposed here) just sleep
log "Initial DB settle wait ${STARTUP_WAIT_DB}s"
sleep "$STARTUP_WAIT_DB"

# Stage 2: app health
retry_wait "$APP_HEALTH_URL" "$STARTUP_WAIT_APP" app

# Stage 3: embedding endpoint (optional)
if [ -n "$EMBED_HEALTH_URL" ]; then
  retry_wait "$EMBED_HEALTH_URL" "$STARTUP_WAIT_EMBED" embed || {
    log "embed health not ready; exiting"
    exit 1
  }
fi

# Extra buffer
log "Extra post-health sleep ${EXTRA_SLEEP_AFTER}s"
sleep "$EXTRA_SLEEP_AFTER"

log "Launching embedding worker"
exec python app/inference/gating.py --db-url "$DATABASE_URL"
