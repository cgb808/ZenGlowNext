"""Lightweight resource usage watchdog.

Periodically samples process CPU and RSS. Emits structured log lines when
either crosses configured thresholds. Designed to be cheap: avoids threads
if disabled; single background thread with sleep otherwise.

Environment variables:
  RESOURCE_WATCH_INTERVAL_SEC (default 15)
  RESOURCE_CPU_HIGH_PCT (default 85)
  RESOURCE_MEM_HIGH_MB (default 1400)  # adapt to 2G container limit
  RESOURCE_WATCH_ENABLED (default 1)

Log events (component=resource_watch):
  resource_usage - routine sample (debug level)
  resource_high  - threshold breach (info level)
"""

from __future__ import annotations

import os
import threading
import time
import psutil  # type: ignore
import logging

from .logging import with_ctx

log = with_ctx(logging.getLogger(__name__), component="resource_watch")

_started = False
_lock = threading.Lock()


def _conf_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def start(background: bool = True) -> None:
    global _started
    if os.getenv("RESOURCE_WATCH_ENABLED", "1") not in {"1", "true", "yes"}:
        return
    with _lock:
        if _started:
            return
        _started = True
    interval = _conf_int("RESOURCE_WATCH_INTERVAL_SEC", 15)
    cpu_high = _conf_int("RESOURCE_CPU_HIGH_PCT", 85)
    mem_high_mb = _conf_int("RESOURCE_MEM_HIGH_MB", 1400)
    proc = psutil.Process()

    def run():  # pragma: no cover - background sampling
        # Initial warm-up for cpu_percent baseline
        proc.cpu_percent(interval=None)
        while True:
            try:
                cpu = proc.cpu_percent(interval=None)  # non-block after warm
                rss = proc.memory_info().rss // (1024 * 1024)
                if cpu >= cpu_high or rss >= mem_high_mb:
                    log(
                        "resource_high",
                        cpu_pct=cpu,
                        rss_mb=rss,
                        cpu_high_pct=cpu_high,
                        mem_high_mb=mem_high_mb,
                    )
                else:
                    # Lower verbosity event for trace/debug if needed
                    logging.getLogger(__name__).debug(
                        "resource_usage", extra={"cpu_pct": cpu, "rss_mb": rss}
                    )
            except Exception as e:  # noqa: BLE001
                log("resource_watch_error", error=str(e))
            time.sleep(interval)

    t = threading.Thread(target=run, name="resource-watch", daemon=True)
    t.start()
