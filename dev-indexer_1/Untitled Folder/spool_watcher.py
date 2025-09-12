#!/usr/bin/env python3
from __future__ import annotations
import os, time, sys, argparse
from pathlib import Path

try:
    from watchdog.observers import Observer  # type: ignore
    from watchdog.events import FileSystemEventHandler  # type: ignore
except Exception as e:  # noqa: BLE001
    print("watchdog not installed; please pip install watchdog", file=sys.stderr)
    raise


def bytes_of_msgpacks(p: Path) -> int:
    total = 0
    for f in p.glob("*.msgpack"):
        try:
            total += f.stat().st_size
        except FileNotFoundError:
            pass
    return total


class TriggerHandler(FileSystemEventHandler):
    def __init__(self, incoming: Path, threshold_bytes: int, process_script: str, lock_file: str):
        self.incoming = incoming
        self.threshold = threshold_bytes
        self.process_script = process_script
        self.lock_file = Path(lock_file)

    def maybe_trigger(self):
        size = bytes_of_msgpacks(self.incoming)
        if size < self.threshold:
            return
        # lock to prevent concurrent runs
        try:
            fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            return
        try:
            print(f"[watcher] threshold met ({size} bytes) -> running {self.process_script}")
            rc = os.system(self.process_script)
            if rc != 0:
                print(f"[watcher] process script exited with {rc}")
        finally:
            os.close(fd)
            try:
                os.unlink(self.lock_file)
            except FileNotFoundError:
                pass

    # Debounce on any event
    def on_any_event(self, event):  # type: ignore[override]
        self.maybe_trigger()


def main():
    ap = argparse.ArgumentParser(description="Spool watcher to trigger ingestion when size threshold exceeded")
    ap.add_argument('--spool-dir', default=os.getenv('SPOOL_DIR','./data/spool'))
    ap.add_argument('--threshold-mb', type=int, default=int(os.getenv('SPOOL_TRIGGER_SIZE_MB','100')))
    ap.add_argument('--process-script', default=os.getenv('PROCESS_SPOOL_SCRIPT_PATH','./scripts/process_spool.sh'))
    ap.add_argument('--lock-file', default=os.getenv('LOCK_FILE','/tmp/spool_watcher.lock'))
    args = ap.parse_args()

    incoming = Path(args.spool_dir) / 'incoming'
    incoming.mkdir(parents=True, exist_ok=True)

    handler = TriggerHandler(incoming, args.threshold_mb * 1024 * 1024, args.process_script, args.lock_file)
    obs = Observer()
    obs.schedule(handler, str(incoming), recursive=False)
    obs.start()
    print(f"[watcher] watching {incoming} (threshold {args.threshold_m b} MB)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        obs.stop()
        obs.join()


if __name__ == '__main__':
    raise SystemExit(main())
