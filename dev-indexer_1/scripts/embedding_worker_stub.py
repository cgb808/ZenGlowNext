#!/usr/bin/env python3
"""Minimal Redis-subscribing embedding worker stub.

Listens for ingestion events and starts embedding/indexing for a given batch_tag.
This is a scaffold—replace the TODO with real embedding/indexing logic.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from typing import Any, Dict

import redis  # type: ignore


def get_redis():  # pragma: no cover
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        socket_timeout=5,
    )


def handle_event(evt: Dict[str, Any]) -> None:
    etype = evt.get("type")
    content = evt.get("content") or {}
    if etype in ("ingest.ready", "ingest.manifest", "pg_notify"):
        batch_tag = content.get("batch_tag") or evt.get("batch_tag")
        status = content.get("status") or evt.get("status")
        if not batch_tag:
            return
        # TODO: Replace with real embedding pipeline: query manifest/doc rows by batch_tag
        print(f"[worker] Received {etype} for batch_tag={batch_tag} status={status}")
        # Example placeholder: sleep to simulate work
        time.sleep(0.1)


def main() -> int:  # pragma: no cover
    r = get_redis()
    channels = [
        os.getenv("EMBED_SUB_CHANNEL", "pg_events:ingest.manifest"),
        os.getenv("EMBED_READY_CHANNEL", "pg_events:ingest.ready"),
    ]
    print(f"[worker] Subscribing to: {channels}")
    pubsub = r.pubsub()
    pubsub.subscribe(*channels)

    def _term(signum, frame):
        try:
            pubsub.close()
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, _term)
    signal.signal(signal.SIGTERM, _term)

    for m in pubsub.listen():
        if m.get("type") != "message":
            continue
        data = m.get("data")
        if data is None:
            continue
        try:
            if isinstance(data, (bytes, bytearray)):
                evt = json.loads(data.decode("utf-8", errors="ignore"))
            elif isinstance(data, str):
                evt = json.loads(data)
            else:
                continue
            if not isinstance(evt, dict):
                continue
        except Exception:
            continue
        handle_event(evt)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
