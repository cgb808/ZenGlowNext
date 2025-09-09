#!/usr/bin/env python3
"""Polling watcher for spool directory.

Triggers process_spool.sh when the total size of *.msgpack in incoming/ exceeds a threshold
or when a minimum file count is reached. Uses stdlib only (no watchdog dep).

Env/CLI:
  --spool-dir (/data/spool)
  --min-bytes (default 4_000_000)
  --min-files (default 1)
  --interval-sec (default 5)
  --script (path to process_spool.sh)
"""
from __future__ import annotations
import argparse, os, sys, time, subprocess
from pathlib import Path


def parse_args():
    ap = argparse.ArgumentParser(description="Poll spool incoming and trigger orchestrator when threshold met")
    ap.add_argument('--spool-dir', default=os.getenv('SPOOL_DIR', '/data/spool'))
    ap.add_argument('--min-bytes', type=int, default=int(os.getenv('SPOOL_MIN_BYTES', '4000000')))
    ap.add_argument('--min-files', type=int, default=int(os.getenv('SPOOL_MIN_FILES', '1')))
    ap.add_argument('--interval-sec', type=float, default=float(os.getenv('SPOOL_POLL_INTERVAL', '5')))
    ap.add_argument('--script', default=os.getenv('SPOOL_PROCESS_SCRIPT'))
    return ap.parse_args()


def incoming_stats(incoming: Path) -> tuple[int, int]:
    total = 0
    count = 0
    for p in incoming.glob('*.msgpack'):
        try:
            st = p.stat()
            total += st.st_size
            count += 1
        except FileNotFoundError:
            continue
    return total, count


def main():
    args = parse_args()
    spool = Path(args.spool_dir)
    incoming = spool / 'incoming'
    if not incoming.exists():
        incoming.mkdir(parents=True, exist_ok=True)
    script = args.script or str((Path(__file__).parent / 'process_spool.sh').resolve())
    print(f"[spool-watcher] dir={incoming} min_bytes={args.min_bytes} min_files={args.min_files} interval={args.interval_sec}s script={script}")
    while True:
        try:
            total, count = incoming_stats(incoming)
            if (count >= args.min_files) and (total >= args.min_bytes):
                print(f"[trigger] count={count} bytes={total} -> {script}")
                # Run orchestrator; do not overlap runs
                proc = subprocess.run([script], check=False)
                rc = proc.returncode
                print(f"[complete] orchestrator exit={rc}")
            time.sleep(args.interval_sec)
        except KeyboardInterrupt:
            print("[spool-watcher] exit")
            return 0
        except Exception as e:  # noqa: BLE001
            print(f"[spool-watcher] error: {e}")
            time.sleep(max(1.0, args.interval_sec))


if __name__ == '__main__':
    raise SystemExit(main())
