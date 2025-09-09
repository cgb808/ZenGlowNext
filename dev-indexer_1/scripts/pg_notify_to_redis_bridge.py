"""Postgres → Redis notification bridge (JSON-aware, dynamic channel forwarding).

Listens to Postgres NOTIFY channel(s) (e.g. `engagement_updates`) and republishes
structured messages onto Redis Pub/Sub channels for downstream workers or
real-time dashboards.

Env:
    DATABASE_URL            Postgres DSN (required)
    PG_LISTEN_CHANNELS      Comma-separated channels (default: engagement_updates)
    REDIS_HOST              Redis host (default: localhost)
    REDIS_PORT              Redis port (default: 6379)
    REDIS_DB                Redis DB index (default: 0)
    REDIS_PASSWORD          Redis password (optional)
    REDIS_PREFIX            Prefix for outgoing channels (default: 'pg_events:')
    LOG_LEVEL               INFO|DEBUG (default INFO)

Behavior:
    - Expects JSON payload in NOTIFY; falls back to simple text when not JSON.
    - Publishes to Redis channel f"{REDIS_PREFIX}{pg_channel}".

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
from typing import List

import psycopg2  # type: ignore
import psycopg2.extensions  # type: ignore
import redis  # type: ignore

def _get_logger() -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="[%(asctime)s] %(levelname)s %(message)s")
    return logging.getLogger("pg_notify_bridge")


logger = _get_logger()


def _connect_pg(dsn: str) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(dsn)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
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
    prefix = os.getenv("REDIS_PREFIX", "pg_events:")
    route_by_type = os.getenv("REDIS_ROUTE_BY_TYPE", "true").lower() == "true"

    backoff = 1.0
    r = _connect_redis()
    while True:
        try:
            logger.info(f"Connecting to Postgres and LISTEN on: {channels}")
            conn = _connect_pg(dsn)
            cur = conn.cursor()
            for ch in channels:
                cur.execute(f"LISTEN {ch};")
            logger.info("Bridge running. Waiting for notifications…")
            backoff = 1.0  # reset after successful connect

            while True:
                # Wait for up to 5 seconds for a notification
                if select.select([conn], [], [], 5) == ([], [], []):
                    continue
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    payload_raw = notify.payload or ""
                    # Try parse as JSON object
                    try:
                        obj = json.loads(payload_raw)
                        if not isinstance(obj, dict):
                            raise ValueError("non-object JSON")
                        msg = obj
                        msg.setdefault("type", "pg_notify")
                        msg.setdefault("channel", notify.channel)
                        msg.setdefault("ts", datetime.now(timezone.utc).isoformat())
                    except Exception:
                        msg = {
                            "type": "pg_notify",
                            "channel": notify.channel,
                            "payload": payload_raw,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }

                    # Always publish to the default (by PG channel)
                    out_channels = [f"{prefix}{notify.channel}"]
                    # Optionally also route by payload 'type' (and action), e.g., pg_events:ingest.manifest
                    if route_by_type and isinstance(msg, dict):
                        mtype = msg.get("type")
                        action = msg.get("action")
                        if isinstance(mtype, str) and mtype:
                            out_channels.append(f"{prefix}{mtype}")
                            if isinstance(action, str) and action:
                                out_channels.append(f"{prefix}{mtype}.{action.lower()}")

                    payload = json.dumps(msg)
                    for out_channel in out_channels:
                        try:
                            r.publish(out_channel, payload)
                            logger.debug(f"Published to Redis {out_channel}: {msg}")
                        except Exception as e:  # Redis failure fallback
                            logger.error(f"Redis publish failed to {out_channel}: {e}")
        except Exception as e:
            logger.error(f"Bridge error: {e}")
            logger.info(f"Reconnecting in {backoff:.1f}s …")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
            continue


if __name__ == "__main__":  # pragma: no cover
    main()
