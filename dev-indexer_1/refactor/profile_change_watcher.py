#!/usr/bin/env python3
"""Profile Change Watcher

Polls family/member/profile tables for a target member (default: Charles Bowen) and
emits a log entry (and optional Redis publish / webhook) when any field changes.

Features:
  * Periodic checksum (stable JSON hash) of consolidated row
  * Field-level diff list (keys whose values changed, ignoring updated_at if only timestamp churn)
  * Optional Redis publish (channel PROFILE_CHANGE) with msgpack payload
  * Optional webhook POST with JSON payload
  * Single-run mode (--once) for scripting / cron integration

Usage examples:
  python scripts/profile_change_watcher.py --dsn "$DATABASE_URL" --interval 15 \
      --full-name "Charles Bowen" --redis-url redis://localhost:6379

  # One-shot poll (exit 0 regardless of change):
  python scripts/profile_change_watcher.py --once --full-name "Alice" --dsn $DATABASE_URL

Environment fallbacks:
  --dsn defaults to DATABASE_URL / SUPABASE_DB_URL / SUPABASE_DIRECT_URL.
"""
from __future__ import annotations

import os, time, json, argparse, hashlib, psycopg
from typing import Any, Dict, Optional
from psycopg.rows import dict_row


def fetch_profile(conn, full_name: str) -> Optional[Dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT m.id as member_id, m.full_name, m.role,
                   f.family_key, f.display_name as family_display_name,
                   p.preferences, p.traits, p.updated_at
            FROM family_members m
            JOIN families f ON f.id = m.family_id
            LEFT JOIN member_profiles p ON p.member_id = m.id
            WHERE m.full_name = %s
            LIMIT 1
            """,
            (full_name,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def stable_hash(obj: Dict[str, Any]) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def diff_keys(prev: Dict[str, Any], curr: Dict[str, Any]) -> list[str]:
    changed = []
    for k in sorted(set(prev.keys()) | set(curr.keys())):
        if k == "updated_at":  # allow timestamp churn alone to be considered separately
            continue
        if prev.get(k) != curr.get(k):
            changed.append(k)
    return changed


def publish_redis(redis_url: str, payload: dict):
    try:
        import redis, msgpack  # type: ignore
        r = redis.from_url(redis_url)
        packed: bytes = msgpack.packb(payload, use_bin_type=True)  # type: ignore[assignment]
        r.publish("PROFILE_CHANGE", packed)
    except Exception as e:  # noqa: BLE001
        print(f"[redis] publish failed: {e}")


def post_webhook(url: str, payload: dict):
    try:
        import requests  # type: ignore

        requests.post(url, json=payload, timeout=5)
    except Exception as e:  # noqa: BLE001
        print(f"[webhook] post failed: {e}")


def resolve_dsn(cli_dsn: Optional[str]) -> Optional[str]:
    return (
        cli_dsn
        or os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("SUPABASE_DIRECT_URL")
    )


def main():  # pragma: no cover - runtime logic
    ap = argparse.ArgumentParser(description="Poll for member profile changes")
    ap.add_argument("--dsn", help="Postgres DSN (fallback to env)")
    ap.add_argument("--full-name", default="Charles Bowen", help="Target member full_name")
    ap.add_argument("--interval", type=int, default=20, help="Polling interval seconds")
    ap.add_argument("--redis-url", help="Redis URL for pub/sub notification")
    ap.add_argument("--webhook", help="Webhook URL for JSON POST on change")
    ap.add_argument("--once", action="store_true", help="Run a single poll then exit")
    args = ap.parse_args()

    dsn = resolve_dsn(args.dsn)
    if not dsn:
        raise SystemExit("Provide --dsn or set DATABASE_URL / SUPABASE_DB_URL")

    prev_hash: Optional[str] = None
    prev_row: Optional[Dict[str, Any]] = None
    print(
        f"[watch] starting full_name='{args.full_name}' interval={args.interval}s redis={'yes' if args.redis_url else 'no'} webhook={'yes' if args.webhook else 'no'}"
    )
    while True:
        try:
            with psycopg.connect(dsn) as conn:
                row = fetch_profile(conn, args.full_name)
            if not row:
                print(f"[watch] member not found: {args.full_name}")
            else:
                current_hash = stable_hash(row)
                if prev_hash and current_hash != prev_hash:
                    changed = diff_keys(prev_row or {}, row)
                    payload = {
                        "event": "profile_change",
                        "full_name": args.full_name,
                        "timestamp": time.time(),
                        "changed_keys": changed,
                        "row": row,
                    }
                    print(
                        f"[change] hash={current_hash[:12]} keys={','.join(changed) if changed else '(only updated_at)'}"
                    )
                    if args.redis_url:
                        publish_redis(args.redis_url, payload)
                    if args.webhook:
                        post_webhook(args.webhook, payload)
                prev_hash = current_hash
                prev_row = row
        except Exception as e:  # noqa: BLE001
            print(f"[error] {e}")
        if args.once:
            break
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
