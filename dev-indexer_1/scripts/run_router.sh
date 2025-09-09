#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ROUTER_DIR="$REPO_ROOT/grpc-router"
BIN="$ROUTER_DIR/bin/router"
ADDR="${ADDR:-:50052}"

if [[ ! -x "$BIN" ]]; then
  echo "[run_router] router binary not found, attempting to build..." >&2
  ( cd "$ROUTER_DIR" && mkdir -p bin && make Gen-go && go build -o bin/router ./cmd/router )
fi

echo "[run_router] starting router at $ADDR" >&2
exec "$BIN" -addr "$ADDR" "$@"
