"""System metrics collection (CPU, memory, GPU) with lightweight caching.

This module is isolated so we can silence mypy noise from dynamic libs.
"""

# mypy: ignore-errors
from __future__ import annotations

import os
import subprocess
import time
import json
from typing import Any, Dict, List

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore

try:
    import pynvml  # type: ignore
except Exception:  # pragma: no cover
    pynvml = None  # type: ignore

_CACHE: Dict[str, Any] | None = None
_CACHE_TS: float | None = None
_TTL = 2.0  # base TTL for expensive metrics

# Separate shorter TTL for fast-changing lightweight metrics (e.g., docker stats)
_FAST_TTL = 1.0
_FAST_CACHE: Dict[str, Any] | None = None
_FAST_CACHE_TS: float | None = None


def _gpus_via_pynvml() -> List[Dict[str, Any]]:
    g: List[Dict[str, Any]] = []
    if not pynvml:
        return g
    try:
        pynvml.nvmlInit()  # type: ignore
        count = int(pynvml.nvmlDeviceGetCount())  # type: ignore
        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)  # type: ignore
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)  # type: ignore
            util = pynvml.nvmlDeviceGetUtilizationRates(h)  # type: ignore
            temp = int(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))  # type: ignore
            raw_name = pynvml.nvmlDeviceGetName(h)  # type: ignore
            name = raw_name.decode() if isinstance(raw_name, bytes) else str(raw_name)
            total_mb = int(mem.total / (1024 * 1024))
            used_mb = int(mem.used / (1024 * 1024))
            g.append(
                {
                    "index": i,
                    "name": name,
                    "memory_total_mb": total_mb,
                    "memory_used_mb": used_mb,
                    "memory_percent": (
                        round(used_mb / total_mb * 100, 2) if total_mb else 0.0
                    ),
                    "utilization_percent": getattr(util, "gpu", None),
                    "temperature_c": temp,
                }
            )
    except Exception:
        return []
    return g


def _gpus_via_nvidia_smi() -> List[Dict[str, Any]]:
    try:
        out = (
            subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                stderr=subprocess.DEVNULL,
                timeout=1.5,
            )
            .decode()
            .strip()
        )
        g: List[Dict[str, Any]] = []
        if out:
            for idx, line in enumerate(out.splitlines()):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 5:
                    name, mem_total, mem_used, util_gpu, temp = parts
                    total_mb = int(mem_total)
                    used_mb = int(mem_used)
                    g.append(
                        {
                            "index": idx,
                            "name": name,
                            "memory_total_mb": total_mb,
                            "memory_used_mb": used_mb,
                            "memory_percent": (
                                round(used_mb / total_mb * 100, 2) if total_mb else 0.0
                            ),
                            "utilization_percent": float(util_gpu),
                            "temperature_c": int(temp),
                        }
                    )
        return g
    except Exception:
        return []


def _gather_gpu() -> List[Dict[str, Any]]:
    g = _gpus_via_pynvml()
    if g:
        return g
    return _gpus_via_nvidia_smi()


def _gpu_processes() -> List[Dict[str, Any]]:
    """Return active GPU compute processes (best-effort).

    Uses nvidia-smi query; silently returns [] if unsupported.
    """
    try:
        out = (
            subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-compute-apps=pid,process_name,used_memory",
                    "--format=csv,noheader,nounits",
                ],
                stderr=subprocess.DEVNULL,
                timeout=1.5,
            )
            .decode()
            .strip()
        )
        procs: List[Dict[str, Any]] = []
        if not out:
            return procs
        for line in out.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 3:
                continue
            pid_s, name, mem_mb_s = parts
            try:
                procs.append(
                    {
                        "pid": int(pid_s),
                        "process": name,
                        "memory_used_mb": int(mem_mb_s),
                    }
                )
            except Exception:
                continue
        return procs
    except Exception:
        return []


def _docker_stats() -> List[Dict[str, Any]]:
    """Collect docker container stats using `docker stats --no-stream`.

    Returns a list of container dicts. Falls back empty if docker unavailable.
    Uses the Go template JSON output for easier parsing.
    """
    try:
        # Each line becomes a JSON object we parse individually
        cmd = [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{json .}}",
        ]
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2).decode()
        containers: List[Dict[str, Any]] = []
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except Exception:
                continue
            # Normalize / derive numeric fields where possible
            def _parse_percent(val: str) -> float | None:
                if not isinstance(val, str):
                    return None
                val = val.strip().rstrip('%')
                try:
                    return float(val)
                except Exception:
                    return None

            def _parse_bytes(field: str) -> int | None:
                # field examples: "123.5MiB / 7.6GiB" or "512KiB / 0B"
                if not isinstance(field, str) or '/' not in field:
                    return None
                lhs = field.split('/')[0].strip()
                return _human_size_to_bytes(lhs)

            def _human_size_to_bytes(token: str) -> int | None:
                try:
                    import re
                    m = re.match(r"([0-9.]+)\s*([KMGTP]?i?)?B", token, re.I)
                    if not m:
                        return None
                    num = float(m.group(1))
                    unit = (m.group(2) or '').lower()
                    scale_map = {
                        '': 1,
                        'k': 1000,
                        'ki': 1024,
                        'm': 1000**2,
                        'mi': 1024**2,
                        'g': 1000**3,
                        'gi': 1024**3,
                        't': 1000**4,
                        'ti': 1024**4,
                        'p': 1000**5,
                        'pi': 1024**5,
                    }
                    scale = scale_map.get(unit, 1)
                    return int(num * scale)
                except Exception:
                    return None

            cpu_perc = _parse_percent(raw.get('CPUPerc'))
            mem_perc = _parse_percent(raw.get('MemPerc'))
            mem_usage_field = raw.get('MemUsage')
            mem_used_bytes = _parse_bytes(mem_usage_field) if mem_usage_field else None

            containers.append(
                {
                    'id': raw.get('ID'),
                    'name': raw.get('Name'),
                    'cpu_percent': cpu_perc,
                    'memory_used_bytes': mem_used_bytes,
                    'memory_percent': mem_perc,
                    'net_io': raw.get('NetIO'),
                    'block_io': raw.get('BlockIO'),
                    'pids': raw.get('PIDs'),
                }
            )
        return containers
    except Exception:
        return []


def _fast_metrics() -> Dict[str, Any]:
    """Metrics gathered at faster cadence (docker stats, GPU procs)."""
    global _FAST_CACHE, _FAST_CACHE_TS
    now = time.time()
    if _FAST_CACHE and _FAST_CACHE_TS and (now - _FAST_CACHE_TS) < _FAST_TTL:
        return _FAST_CACHE
    data = {
        'containers': _docker_stats(),
        'gpu_processes': _gpu_processes(),
    }
    _FAST_CACHE = data
    _FAST_CACHE_TS = now
    return data


def get_system_metrics() -> Dict[str, Any]:  # runtime path
    global _CACHE, _CACHE_TS
    now = time.time()
    if _CACHE and _CACHE_TS and (now - _CACHE_TS) < _TTL:
        # Merge the rapidly changing subset on each call
        merged = dict(_CACHE)
        merged.update(_fast_metrics())
        return merged
    data: Dict[str, Any] = {}
    if psutil:
        try:
            data["cpu_percent"] = float(psutil.cpu_percent(interval=None))
            data["cpu_count"] = int(psutil.cpu_count(logical=True) or 0)
            try:
                la = os.getloadavg()
                data["load_avg"] = tuple(float(x) for x in la)
            except Exception:
                pass
            vm = psutil.virtual_memory()
            data["memory"] = {
                "total_bytes": int(vm.total),
                "available_bytes": int(vm.available),
                "used_bytes": int(vm.used),
                "percent": float(vm.percent),
            }
            sm = psutil.swap_memory()
            data["swap"] = {
                "total_bytes": int(sm.total),
                "used_bytes": int(sm.used),
                "percent": float(sm.percent),
            }
        except Exception:
            pass
    data["gpu"] = _gather_gpu()
    # Always enrich with fast metrics (uncached part will manage its own TTL)
    data.update(_fast_metrics())
    _CACHE = data
    _CACHE_TS = now
    return data
