#!/usr/bin/env python3
"""Watch a directory (or glob) for new RAG msgpack artifacts and replay them.

Uses `rag_replay_msgpack.replay` to insert new chunk records into Postgres.

Strategy:
  * Poll every --interval seconds (default 15)
  * Track processed files via in-memory set + optional state file (--state-file)
  * Supports --reembed / --dummy-fill consistent with replay script
  * Globs are re-evaluated each poll (e.g. 'data/msgpack/*.msgpack')

Example:
  python scripts/rag_replay_watch.py --glob 'data/msgpack/*.msgpack' \
      --interval 10 --dummy-fill 768 --skip-existing

Press Ctrl+C to stop. Safe to restart; previously processed files will be skipped.
"""
from __future__ import annotations

import argparse, glob, os, sys, time, json
from pathlib import Path
from typing import List, Set

# Flexible import so it works whether run from repo root or inside scripts/
try:  # pragma: no cover - import flexibility
    from rag_replay_msgpack import replay  # type: ignore
except ImportError:  # pragma: no cover
    try:
        from scripts.rag_replay_msgpack import replay  # type: ignore
    except ImportError as e:  # pragma: no cover
        print("[fatal] Could not import replay from rag_replay_msgpack; ensure PYTHONPATH includes scripts/", file=sys.stderr)
        raise e

def parse_args():
    ap = argparse.ArgumentParser(description="Watch directory/glob for new msgpack artifacts and replay them")
    ap.add_argument('--glob', required=True, help='Glob pattern for msgpack files')
    ap.add_argument('--interval', type=int, default=15, help='Polling interval seconds')
    ap.add_argument('--reembed', action='store_true', help='Regenerate embeddings even if present')
    ap.add_argument('--dummy-fill', type=int, help='Zero vector dim if embedding missing / fails')
    ap.add_argument('--batch-tag', help='Override batch tag for all rows')
    ap.add_argument('--embed-batch-size', type=int, default=32)
    ap.add_argument('--skip-existing', action='store_true')
    ap.add_argument('--sleep', type=float, default=0.0, help='Sleep between embedding micro-batches')
    ap.add_argument('--state-file', help='Persist processed file list to this JSON file for restart safety')
    ap.add_argument('--dry-run', action='store_true')
    return ap.parse_args()


def load_state(path: str | None) -> Set[str]:
    if not path:
        return set()
    p = Path(path)
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text()))
    except Exception:  # noqa: BLE001
        return set()


def save_state(path: str | None, processed: Set[str]):
    if not path:
        return
    try:
        Path(path).write_text(json.dumps(sorted(processed)))
    except Exception as e:  # noqa: BLE001
        print(f"[warn] Failed to save state: {e}")


def main():  # pragma: no cover
    args = parse_args()
    processed = load_state(args.state_file)
    print(f"[watch] Starting; already have {len(processed)} processed entries")
    try:
        while True:
            paths: List[Path] = [Path(p) for p in glob.glob(args.glob, recursive=True)]
            new_files = [p for p in paths if p.is_file() and str(p) not in processed]
            if new_files:
                new_files.sort(key=lambda p: p.stat().st_mtime)
                print(f"[watch] Found {len(new_files)} new file(s)")
                try:
                    replay(new_files, args.reembed, args.dummy_fill, args.batch_tag, args.embed_batch_size, args.dry_run, args.skip_existing, args.sleep)
                except SystemExit:  # propagate config issues
                    raise
                except Exception as e:  # noqa: BLE001
                    print(f"[error] Replay failed: {e}")
                for f in new_files:
                    processed.add(str(f))
                save_state(args.state_file, processed)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[watch] Stopped by user")
        save_state(args.state_file, processed)
        return 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
