#!/usr/bin/env python3
"""
Filesystem watcher that triggers ingestion when total .msgpack size
in the spool incoming directory exceeds a threshold.
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler  # type: ignore
from watchdog.observers import Observer  # type: ignore

SPOOL_DIR = Path(os.getenv("SPOOL_DIR", "./data/spool"))
INCOMING_DIR = SPOOL_DIR / "incoming"
TRIGGER_SIZE_BYTES = int(float(os.getenv("SPOOL_TRIGGER_SIZE_MB", "100")) * 1024 * 1024)
PROCESS_SCRIPT_PATH = Path(os.getenv("PROCESS_SPOOL_SCRIPT_PATH", "./scripts/process_spool.sh")).resolve()
LOCK_FILE = Path(os.getenv("LOCK_FILE", "/tmp/spool_watcher.lock"))

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")


def total_msgpack_size_bytes(directory: Path) -> int:
    total = 0
    if not directory.exists():
        return 0
    for p in directory.glob("*.msgpack"):
        try:
            total += p.stat().st_size
        except OSError:
            # File might be in-flight; skip this round
            pass
    return total


def check_and_trigger() -> None:
    if LOCK_FILE.exists():
        logging.warning("Processing already in progress (lock present). Skipping trigger.")
        return

    size = total_msgpack_size_bytes(INCOMING_DIR)
    logging.info(
        "Current spool size: %.2f MB (threshold: %.2f MB)",
        size / (1024 * 1024),
        TRIGGER_SIZE_BYTES / (1024 * 1024),
    )
    if size < TRIGGER_SIZE_BYTES:
        return

    try:
        LOCK_FILE.write_text(str(os.getpid()))
        logging.info("Size threshold reached. Triggering ingestion: %s", PROCESS_SCRIPT_PATH)
        subprocess.run([str(PROCESS_SCRIPT_PATH)], check=True)
        logging.info("Ingestion process finished.")
    except Exception as e:  # noqa: BLE001
        logging.error("Error during trigger: %s", e)
    finally:
        if LOCK_FILE.exists():
            try:
                LOCK_FILE.unlink()
            except OSError:
                pass


class SpoolHandler(FileSystemEventHandler):
    def on_created(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory and event.src_path.endswith(".msgpack"):
            logging.info("New file detected: %s. Checking threshold soon...", event.src_path)
            time.sleep(2)
            check_and_trigger()


def main() -> int:
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    check_and_trigger()

    handler = SpoolHandler()
    observer = Observer()
    observer.schedule(handler, str(INCOMING_DIR), recursive=False)
    logging.info("Starting spool watcher: %s", INCOMING_DIR)
    observer.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
