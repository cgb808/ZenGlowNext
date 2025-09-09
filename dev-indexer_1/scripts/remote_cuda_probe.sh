#!/usr/bin/env bash
set -euo pipefail

HOST=${CUDA_REMOTE_HOST:-}
USER=${CUDA_REMOTE_USER:-}
KEY=${CUDA_REMOTE_SSH_KEY:-}

if [[ -z "${HOST}" || -z "${USER}" || -z "${KEY}" ]]; then
  echo "Missing CUDA_REMOTE_* env (HOST/USER/SSH_KEY)." >&2
  exit 2
fi

# Quick ICMP + SSH probe
ping -c 1 -W 1 "$HOST" >/dev/null 2>&1 && echo "ICMP: OK ($HOST)" || echo "ICMP: FAIL ($HOST)"
ssh -o BatchMode=yes -o ConnectTimeout=2 -i "$KEY" "$USER@$HOST" nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null \
  && echo "SSH: OK (nvidia-smi)" \
  || echo "SSH: FAIL"
