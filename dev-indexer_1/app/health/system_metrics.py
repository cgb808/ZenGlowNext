"""System metrics helper for health router.

Provides a lightweight snapshot of CPU, memory, and basic uptime data
without heavy dependencies. Safe to import in minimal environments.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - stub psutil
    psutil = None  # type: ignore

_START_TIME = time.time()


def get_system_metrics() -> Dict[str, Any]:
    cpu = None
    mem_percent = None
    if psutil is not None:
        try:
            cpu = float(psutil.cpu_percent(interval=0.05))
        except Exception:
            cpu = None
        try:
            vm = psutil.virtual_memory()
            mem_percent = float(vm.percent)
        except Exception:
            mem_percent = None
    return {
        "timestamp": int(time.time() * 1000),
        "uptime_seconds": int(time.time() - _START_TIME),
        "cpu_percent": cpu if cpu is not None else 0.0,
        "memory_percent": mem_percent if mem_percent is not None else 0.0,
        "hostname": os.getenv("HOSTNAME"),
    }


__all__ = ["get_system_metrics"]
