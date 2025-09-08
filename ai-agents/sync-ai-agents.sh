#!/usr/bin/env bash
# Sync helper for large ignored AI agent artifacts.
# Usage:
#   ./ai-agents/sync-ai-agents.sh backup   # copy ignored assets to ../ai-agents-cache
#   ./ai-agents/sync-ai-agents.sh restore  # restore from cache back into working tree
set -euo pipefail
MODE=${1:-}
CACHE_DIR="../ai-agents-cache"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IGNORED_PATTERNS=(
  "*.gguf" "*.tflite" "*.h5" "*.pkl" "*.pb" "*.tar.gz" "vector-store" "venv" "analysis_env" "venv_zenglow"
)
if [[ -z "$MODE" ]]; then
  echo "Specify backup or restore" >&2; exit 1; fi
mkdir -p "$CACHE_DIR"
if [[ $MODE == backup ]]; then
  echo "Backing up ignored assets to $CACHE_DIR" >&2
  rsync -a --prune-empty-dirs $(printf -- '--exclude=%q ' "${IGNORED_PATTERNS[@]}") "$ROOT/" "$CACHE_DIR/" || true
  echo "Done." >&2
elif [[ $MODE == restore ]]; then
  echo "Restoring from $CACHE_DIR" >&2
  rsync -a "$CACHE_DIR/" "$ROOT/" || true
  echo "Done." >&2
else
  echo "Unknown mode: $MODE" >&2; exit 1
fi
