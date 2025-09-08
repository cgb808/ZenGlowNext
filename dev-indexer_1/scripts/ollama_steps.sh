#!/usr/bin/env bash
# Granular Ollama setup steps.
# Usage: STEP=<1|2|3|4|5> bash dev-indexer_1/scripts/ollama_steps.sh
# Steps:
# 1: Prepare storage (optional ZFS dataset + dir)
# 2: Install Ollama binary + service enable
# 3: Configure systemd overrides (model dir, keep-alive, max loaded)
# 4: Pull gemma:2b model (idempotent) and optional quant variant (gemma2b-q4)
# 5: Smoke test API generate & list models
set -euo pipefail
STEP=${STEP:-}
if [[ -z "$STEP" ]]; then echo "Set STEP=1..5" >&2; exit 2; fi

# Defaults / overridable
DEFAULT_TANK_DIR=/tank/ollama/models
if [[ -d /tank && -w /tank ]]; then
  OLLAMA_MODELS_DIR=${OLLAMA_MODELS_DIR:-$DEFAULT_TANK_DIR}
else
  # Fallback to home if /tank missing or not writable.
  OLLAMA_MODELS_DIR=${OLLAMA_MODELS_DIR:-$HOME/ollama-models}
fi
OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE:-300}
OLLAMA_MAX_LOADED_MODELS=${OLLAMA_MAX_LOADED_MODELS:-1}
CREATE_Q4_VARIANT=${CREATE_Q4_VARIANT:-1}
REQUIRE_ZFS=${REQUIRE_ZFS:-0}
REQUIRE_HOST=${REQUIRE_HOST:-}

if [[ -n "$REQUIRE_HOST" ]]; then
  CUR_HOST=$(hostname -f 2>/dev/null || hostname)
  if [[ "$CUR_HOST" != "$REQUIRE_HOST" ]]; then
    echo "[guard] Host mismatch: current=$CUR_HOST expected=$REQUIRE_HOST. Aborting." >&2
    exit 10
  fi
fi

log(){ printf '\n[STEP %s] %s\n' "$STEP" "$*"; }

case "$STEP" in
  1)
    log "Host: $(hostname -f 2>/dev/null || hostname) User:$USER"
    log "Requested models dir: ${OLLAMA_MODELS_DIR} (require_zfs=${REQUIRE_ZFS})"
    if [[ "$OLLAMA_MODELS_DIR" == "$DEFAULT_TANK_DIR" ]]; then
      if [[ ! -d /tank ]]; then
        if [[ "$REQUIRE_ZFS" == "1" ]]; then
          log "/tank missing and REQUIRE_ZFS=1 — aborting (create pool/dataset first)."
          exit 4
        else
          log "/tank not present; either create a ZFS pool (see storage_validate.sh) or set OLLAMA_MODELS_DIR explicitly. Falling back to $HOME/ollama-models."
          OLLAMA_MODELS_DIR="$HOME/ollama-models"
        fi
      elif [[ ! -w /tank ]]; then
        if [[ "$REQUIRE_ZFS" == "1" ]]; then
          log "/tank exists but not writable and REQUIRE_ZFS=1 — fix permissions or create dataset."
          exit 5
        else
          log "/tank not writable; falling back to home directory."
          OLLAMA_MODELS_DIR="$HOME/ollama-models"
        fi
      fi
    fi
    if command -v zfs >/dev/null 2>&1; then
      DATASET=$(dirname "$OLLAMA_MODELS_DIR")
      POOL=${DATASET%%/*}
      if [[ "$OLLAMA_MODELS_DIR" == "$DEFAULT_TANK_DIR" ]] && ! zfs list "$DATASET" >/dev/null 2>&1 && zfs list "$POOL" >/dev/null 2>&1; then
        log "Creating ZFS dataset $DATASET (compression=zstd)"
        sudo zfs create -o compression=zstd -o atime=off "$DATASET" || true
      fi
    fi
    mkdir -p "$OLLAMA_MODELS_DIR"
    ls -ld "$OLLAMA_MODELS_DIR" || true
    log "Final models dir in use: $OLLAMA_MODELS_DIR"
    ;;
  2)
    if command -v ollama >/dev/null 2>&1; then
      log "Ollama already installed: $(ollama --version 2>/dev/null || echo present)"
    else
      log "Installing Ollama"
      curl -fsSL https://ollama.com/install.sh | sh
    fi
    log "Enable/start service"
    sudo systemctl enable --now ollama || true
    systemctl is-active --quiet ollama && echo "ollama active" || systemctl status --no-pager ollama || true
    ;;
  3)
    log "Apply systemd override config"
    sudo mkdir -p /etc/systemd/system/ollama.service.d
    cat <<EOF | sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
[Service]
Environment=OLLAMA_MODELS=${OLLAMA_MODELS_DIR}
Environment=OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE}
Environment=OLLAMA_MAX_LOADED_MODELS=${OLLAMA_MAX_LOADED_MODELS}
EOF
    sudo systemctl daemon-reload || true
    sudo systemctl restart ollama || true
    systemctl is-active --quiet ollama && echo "ollama restarted" || true
    echo "Models dir: $OLLAMA_MODELS_DIR"
    ;;
  4)
    log "Pull gemma:2b"
    if ollama list 2>/dev/null | grep -q '^gemma:2b'; then
      log "gemma:2b already present"
    else
      ollama pull gemma:2b
    fi
    if [[ "$CREATE_Q4_VARIANT" == "1" ]]; then
      if ollama list 2>/dev/null | grep -q '^gemma2b-q4'; then
        log "gemma2b-q4 already exists"
      else
        log "Creating quantized gemma2b-q4 (q4_0)"
        WORKDIR=$(mktemp -d)
        cat <<'MODF' > "$WORKDIR/Modelfile"
FROM gemma:2b
PARAMETER quantize q4_0
MODF
        ollama create gemma2b-q4 -f "$WORKDIR/Modelfile"
        rm -rf "$WORKDIR"
      fi
    fi
    ollama list || true
    ;;
  5)
    log "Smoke test API"
    curl -s http://localhost:11434/api/tags | head -n 20 || true
    curl -s http://localhost:11434/api/generate -d '{"model":"gemma:2b","prompt":"ping"}' | head -n 5 || true
    echo "Suggested .env entries:"
    cat <<ENV
OLLAMA_MODEL=gemma:2b
OLLAMA_HOST=127.0.0.1
OLLAMA_PORT=11434
# or quantized variant:
# OLLAMA_MODEL=gemma2b-q4
ENV
    ;;
  *)
    echo "Invalid STEP=$STEP" >&2; exit 3;
    ;;
 esac
