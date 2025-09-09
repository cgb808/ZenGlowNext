#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SRV_DIR="$REPO_ROOT/grpc/logservice"
BIN="$SRV_DIR/bin/logservice"
ADDR="${ADDR:-:50051}"

if [[ ! -x "$BIN" ]]; then
  echo "[run_logservice] logservice binary not found, attempting to build..." >&2
  ( cd "$SRV_DIR" && mkdir -p bin && make gen-go && go build -o bin/logservice ./cmd/logservice )
fi

echo "[run_logservice] starting logservice at $ADDR" >&2
exec "$BIN" -addr "$ADDR" "$@"
