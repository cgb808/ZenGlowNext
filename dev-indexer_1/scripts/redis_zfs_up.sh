#!/usr/bin/env bash
set -euo pipefail

# ZFS-backed Redis setup + start (no placeholders)
# Requires: zpool/zfs, docker compose, sudo. Uses REDIS_DATA_DIR from .env.

POOL=$(zpool list -H -o name | head -n1)
echo "Using pool: ${POOL}"

# Create datasets (idempotent)
sudo zfs create -o mountpoint=/DEV_ZFS/redis "${POOL}/redis" 2>/dev/null || true
sudo zfs create -o mountpoint=/DEV_ZFS/redis/dev-indexer_1 "${POOL}/redis/dev-indexer_1" 2>/dev/null || true

# Quota and permissions
sudo zfs set quota=5G "${POOL}/redis/dev-indexer_1" || true
sudo mkdir -p /DEV_ZFS/redis/dev-indexer_1
sudo chown -R 999:999 /DEV_ZFS/redis/dev-indexer_1

# Show datasets
zfs list -o name,mountpoint,used,avail | grep -E "${POOL}/redis($|/dev-indexer_1)" || true

# Start Redis via Compose
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

docker compose up -d redis
sleep 2

docker compose ps redis || true

# Verify with redis-cli (host and container)
if command -v redis-cli >/dev/null 2>&1; then
  echo "Host redis-cli ping:" && redis-cli -h 127.0.0.1 -p 6379 ping || true
fi

docker exec rag_redis redis-cli ping || true
