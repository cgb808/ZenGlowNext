#!/usr/bin/env bash
set -euo pipefail

echo "[startup] Launching indexer service (no XRDP)."
exec "$@"
