"""Postgres -> Redis notification bridge.

Listens to Postgres NOTIFY channel(s) (e.g. `engagement_updates`) and republishes
structured messages onto Redis Pub/Sub channels for downstream workers or
real-time dashboards.

Environment Variables:
  DATABASE_URL              Postgres DSN (required)
  PG_LISTEN_CHANNELS        Comma-separated channels (default: engagement_updates)
  REDIS_HOST                Redis host (default: localhost)
  REDIS_PORT                Redis port (default: 6379)
  REDIS_DB                  Redis DB index (default: 0)
  REDIS_PASSWORD            Redis password (optional)
  REDIS_BRIDGE_CHANNEL      Redis destination channel (default: engagement_updates)
  BRIDGE_BATCH_FLUSH_MS     (future) for buffering logic (unused now)

Message Schema (JSON, published to Redis):
  {
    "type": "engagement_update",
    "chunk_id": <int>,
    "raw_payload": <original text payload>,
    "ts": <ISO8601 UTC timestamp>
  }

If the Postgres payload is just the chunk_id numeric string, we parse it; otherwise
we include it as raw_payload.

Reliability Considerations:
  * This bridge provides at-most-once delivery (if the process dies after receiving
    but before publishing, the event is lost). For higher guarantees, persist a
    sequence table and implement ack/replay.
  * Reconnection backoff implemented for transient errors.

Usage:
  python scripts/pg_notify_to_redis_bridge.py
"""

from __future__ import annotations

import json
import logging
import os
import select
import time
from datetime import datetime, timezone
from psycopg import sql
from typing import List

import psycopg  # v3
import redis  # type: ignore

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
)
logger = logging.getLogger("pg_notify_bridge")


def _connect_pg(dsn: str):
    # autocommit for LISTEN; psycopg3 connections default to autocommit False
    conn = psycopg.connect(dsn)
    conn.autocommit = True
    return conn


def _connect_redis():  # -> redis.Redis (omitted for type stub absence)
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        socket_timeout=5,
    )


def main():  # pragma: no cover (integration script)
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL required")

    channels_env = os.getenv("PG_LISTEN_CHANNELS", "engagement_updates")
    channels: List[str] = [c.strip() for c in channels_env.split(",") if c.strip()]
    redis_channel = os.getenv("REDIS_BRIDGE_CHANNEL", "engagement_updates")

    backoff = 1.0
    r = _connect_redis()
    while True:
        try:
            logger.info(f"Connecting to Postgres and LISTEN on: {channels}")
            conn = _connect_pg(dsn)
            cur = conn.cursor()
            for ch in channels:
                cur.execute(sql.SQL("LISTEN {};").format(sql.Identifier(ch)))
            logger.info("Bridge running. Waiting for notifications...")
            backoff = 1.0  # reset after successful connect

            while True:
                # Wait for up to 5 seconds for a notification (socket fileno)
                if select.select([conn.pgconn.socket], [], [], 5) == ([], [], []):
                    continue
                # Consume available notifications
                for notify in list(conn.notifies()):
                    payload = notify.payload or ""
                    chunk_id = None
                    if payload.isdigit():
                        try:
                            chunk_id = int(payload)
                        except ValueError:
                            pass
                    msg = {
                        "type": "engagement_update",
                        "channel": notify.channel,
                        "chunk_id": chunk_id,
                        "raw_payload": payload,
                        "ts": datetime.now(timezone.utc).isoformat(),
                    }
                    try:
                        r.publish(redis_channel, json.dumps(msg))
                        logger.debug(f"Published to Redis {redis_channel}: {msg}")
                    except Exception as e:  # Redis failure fallback
                        logger.error(f"Redis publish failed: {e}")
        except Exception as e:
            logger.error(f"Bridge error: {e}")
            logger.info(f"Reconnecting in {backoff:.1f}s ...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue


if __name__ == "__main__":  # pragma: no cover
    main()
