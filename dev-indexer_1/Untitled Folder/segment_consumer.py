#!/usr/bin/env python3
"""Segment consumer: pop file paths from a Redis list and move/copy them.

Env/CLI:
  --redis-url / REDIS_URL           e.g., redis://localhost:6379/0
  --list-key / LIST_KEY             list key to BRPOP from (default append:segments)
  --dest-dir / DEST_DIR             directory to move/copy segments into (default data/append_logs/incoming)
  --copy                            copy instead of move (default move)
  --timeout / BRPOP_TIMEOUT         BRPOP timeout seconds (default 5)
    --max / MAX_ITEMS                 stop after processing N items (default unlimited)
    --max-items                       alias of --max (for compatibility)
    --set-ttl-seconds / LIST_TTL      if set, EXPIRE the list key when list becomes empty
    --list-ttl                        alias of --set-ttl-seconds (for compatibility)

Requires: redis-py (pip install redis)
"""
from __future__ import annotations
import os, argparse, sys, shutil, time
from pathlib import Path
from typing import Optional, Tuple, cast

try:
    import redis  # type: ignore
except Exception as e:  # noqa: BLE001
    print(f"redis import failed: {e}. Install with: pip install redis", file=sys.stderr)
    raise


def parse_args():
    ap = argparse.ArgumentParser(description="Consume segment paths from a Redis list and move/copy them")
    ap.add_argument('--redis-url', default=os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    ap.add_argument('--list-key', default=os.getenv('LIST_KEY', 'append:segments'))
    ap.add_argument('--dest-dir', default=os.getenv('DEST_DIR', 'data/append_logs/incoming'))
    ap.add_argument('--copy', action='store_true')
    ap.add_argument('--timeout', type=int, default=int(os.getenv('BRPOP_TIMEOUT', '5')))
    ap.add_argument('--max', type=int, default=int(os.getenv('MAX_ITEMS', '0')))
    ap.add_argument('--max-items', type=int, help='Alias of --max')
    ap.add_argument('--set-ttl-seconds', type=int, default=int(os.getenv('LIST_TTL', '0')))
    ap.add_argument('--list-ttl', type=int, help='Alias of --set-ttl-seconds')
    return ap.parse_args()


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def unique_name(dest_dir: Path, fname: str) -> Path:
    base = Path(fname).name
    candidate = dest_dir / base
    if not candidate.exists():
        return candidate
    stem, dot, ext = base.partition('.')
    i = 1
    while True:
        c = dest_dir / f"{stem}.{i}{('.' + ext) if dot else ''}"
        if not c.exists():
            return c
        i += 1


def main():
    args = parse_args()
    # Back-compat: alias mapping
    if getattr(args, 'max_items', None) is not None:
        args.max = args.max_items  # type: ignore[attr-defined]
    if getattr(args, 'list_ttl', None) is not None:
        args.set_ttl_seconds = args.list_ttl  # type: ignore[attr-defined]
    dest = Path(args.dest_dir)
    ensure_dir(dest)
    r: "redis.Redis" = redis.Redis.from_url(args.redis_url)
    print(f"[consumer] redis={args.redis_url} key={args.list_key} dest={dest}")
    processed = 0
    try:
        while True:
            if args.max and processed >= args.max:
                print("[consumer] max items reached; exiting")
                return 0
            res = r.brpop(args.list_key, timeout=args.timeout)
            if res is None:
                # heartbeat; if configured, set TTL when queue is empty
                if args.set_ttl_seconds > 0:
                    try:
                        if r.llen(args.list_key) == 0:
                            r.expire(args.list_key, args.set_ttl_seconds)
                            print(f"[ttl] set EXPIRE {args.list_key} {args.set_ttl_seconds}s")
                    except Exception as e:  # noqa: BLE001
                        print(f"[ttl] failed to set TTL: {e}")
                continue
            key_bytes, path_bytes = cast(Tuple[bytes, bytes], res)
            src = Path(path_bytes.decode('utf-8'))
            if not src.exists():
                print(f"[warn] path not found: {src}")
                continue
            dst = unique_name(dest, src.name)
            if args.copy:
                shutil.copy2(src, dst)
                print(f"[copy] {src} -> {dst}")
            else:
                shutil.move(str(src), dst)
                print(f"[move] {src} -> {dst}")
            processed += 1
            # Optionally set TTL on list key when empty
            if args.set_ttl_seconds > 0:
                try:
                    if r.llen(args.list_key) == 0:
                        r.expire(args.list_key, args.set_ttl_seconds)
                        print(f"[ttl] set EXPIRE {args.list_key} {args.set_ttl_seconds}s")
                except Exception as e:  # noqa: BLE001
                    print(f"[ttl] failed to set TTL: {e}")
    except KeyboardInterrupt:
        print("[consumer] interrupted; exiting")
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
