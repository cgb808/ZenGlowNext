import os
import time
import asyncio
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import httpx
import psutil
import math
import glob

###############################################################################
# Optional GPU metrics probe (disabled by default)
#
# Rationale: On some developer machines (e.g. AMD iGPU / laptops without NVIDIA
# drivers) the transient import / probe of GPU utilities can trigger confusing
# warnings or attempts to access non‑existent CUDA devices. To keep baseline
# behavior strictly CPU‑only, probing is now opt‑in via ENABLE_GPU_PROBE=1.
#
# When enabled and GPUtil is installed, /metrics/sys will include a "gpus" list
# with lightweight utilization + memory fields. When disabled (default) the
# field will be an empty list, avoiding any CUDA / NVML touches.
###############################################################################

ENABLE_GPU_PROBE = os.getenv("ENABLE_GPU_PROBE", "false").lower() in {"1", "true", "yes"}
if ENABLE_GPU_PROBE:
	try:  # pragma: no cover - optional dependency
		import GPUtil  # type: ignore
	except Exception:  # pragma: no cover - defensive import guard
		GPUtil = None  # type: ignore
else:  # Probe explicitly disabled
	GPUtil = None  # type: ignore

AGG_ENABLE = os.getenv("HEALTH_AGG_ENABLE", "false").lower() in {"1", "true", "yes"}
GATEWAY_BASE = os.getenv("GATEWAY_BASE", "http://localhost:8000")
RAG_API_BASE = os.getenv("RAG_API_BASE", "http://localhost:8000")

app = FastAPI(title="ZenGlow Dev API")


@app.get("/health")
async def root_health():
	return {"ok": True, "service": "api", "ts": int(time.time())}


@app.get("/health/agg")
async def aggregated_health():
	if not AGG_ENABLE:
		return {"aggregator_enabled": False, "note": "Set HEALTH_AGG_ENABLE=true to enable backend aggregation."}

	targets = [
		{"service": "api", "url": "http://localhost:8000/health"},  # self (assuming same proxy)
		{"service": "gateway", "url": f"{GATEWAY_BASE}/rest/v1/get", "ok_status": {200,401,403,404}},
		{"service": "rag", "url": f"{RAG_API_BASE}/health/rag"},
		{"service": "ollama", "url": f"{RAG_API_BASE}/health/ollama"},
	]

	results: List[Dict[str, Any]] = []
	timeout = httpx.Timeout(3.0, connect=1.0)
	async with httpx.AsyncClient(timeout=timeout) as client:
		for t in targets:
			started = time.time()
			ok_status = t.get("ok_status") or {200}
			try:
				resp = await client.get(t["url"])  # type: ignore
				latency_ms = int((time.time() - started) * 1000)
				ok = resp.status_code in ok_status
				results.append({
					"service": t["service"],
					"ok": ok,
					"status": resp.status_code,
					"latency_ms": latency_ms,
				})
			except Exception as e:
				latency_ms = int((time.time() - started) * 1000)
				results.append({
					"service": t["service"],
					"ok": False,
					"error": str(e),
					"latency_ms": latency_ms,
				})

	return {"aggregator_enabled": True, "results": results, "ts": int(time.time())}


def _gpu_snapshot() -> List[Dict[str, Any]]:
	"""Return list of GPU metric dicts (empty when probe disabled or unavailable).

	No exceptions escape this function; failures degrade to an empty list.
	"""
	if not ENABLE_GPU_PROBE or not GPUtil:  # fast path
		return []
	gpus: List[Dict[str, Any]] = []
	try:  # pragma: no cover - hardware specific
		for g in GPUtil.getGPUs():  # type: ignore[attr-defined]
			gpus.append({
				"id": g.id,
				"name": g.name,
				"load": round(g.load * 100, 2),
				"mem_used_mb": int(getattr(g, 'memoryUsed', 0)),
				"mem_total_mb": int(getattr(g, 'memoryTotal', 0)),
				"temperature": getattr(g, 'temperature', None),
			})
	except Exception:
		return []
	return gpus


def build_system_metrics() -> Dict[str, Any]:
	cpu_percent = psutil.cpu_percent(interval=0.05)
	vm = psutil.virtual_memory()
	swap = psutil.swap_memory()
	# Disk usage (root filesystem) - extend later for multiple mounts if needed
	try:
		disk = psutil.disk_usage('/')
	except Exception:
		disk = None
	temps: Dict[str, Any] = {}
	try:
		temps_raw = psutil.sensors_temperatures()  # type: ignore
		for k, arr in temps_raw.items():
			if arr:
				temps[k] = [{"label": t.label or k, "current": t.current} for t in arr[:4]]
	except Exception:
		pass
	# Derive a simplified cpu_temp (average of first group if available)
	cpu_temp = None
	try:
		for group, arr in temps.items():  # type: ignore
			if arr:
				vals = [x.get('current') for x in arr if isinstance(x.get('current'), (int, float))]
				if vals:
					cpu_temp = round(sum(vals)/len(vals), 1)
					break
	except Exception:
		cpu_temp = None
	load1 = load5 = load15 = 0.0
	try:
		load1, load5, load15 = os.getloadavg()  # type: ignore
	except Exception:
		pass
	gpus = _gpu_snapshot()

	# Network interfaces snapshot
	net_if_stats = psutil.net_if_stats()
	net_io = psutil.net_io_counters(pernic=True)
	# Detect bonding interfaces
	bond_files = glob.glob('/proc/net/bonding/*')
	bond_ifaces = {os.path.basename(p): p for p in bond_files}
	bond_members: Dict[str, list] = {}
	for bname, path in bond_ifaces.items():
		try:
			members = []
			with open(path,'r') as f:
				for line in f:
					if line.startswith('Slave Interface:'):
						members.append(line.split(':',1)[1].strip())
			bond_members[bname] = members
		except Exception:
			bond_members[bname] = []

	def classify_iface(name: str) -> str:
		if name in bond_ifaces:
			return 'bond'
		wireless_dir = f'/sys/class/net/{name}/wireless'
		if os.path.isdir(wireless_dir):
			return 'wifi'
		if name.startswith(('wl', 'wlan')):
			return 'wifi'
		if name.startswith(('en', 'eth', 'em', 'eno', 'ens')):
			return 'lan'
		return 'other'

	interfaces = []
	for name, st in net_if_stats.items():
		if name == 'lo':
			continue
		io = net_io.get(name)
		iface_type = classify_iface(name)
		interfaces.append({
			'name': name,
			'type': iface_type,
			'is_up': st.isup,
			'mtu': st.mtu,
			'speed_mbps': st.speed if getattr(st, 'speed', 0) else None,
			'bytes_sent': getattr(io, 'bytes_sent', None),
			'bytes_recv': getattr(io, 'bytes_recv', None),
			'bond_members': bond_members.get(name) if iface_type == 'bond' else None,
		})

	return {
		"ts": int(time.time() * 1000),
		"cpu": {"percent": cpu_percent, "load": {"1m": load1, "5m": load5, "15m": load15}, "temperature": cpu_temp},
		"memory": {
			"total_mb": int(vm.total / 1024 / 1024),
			"used_mb": int((vm.total - vm.available) / 1024 / 1024),
			"percent": vm.percent,
			"swap_mb": int(swap.used / 1024 / 1024),
		},
		"disk": ({
			"total_gb": int(disk.total/1024/1024/1024),
			"used_gb": int(disk.used/1024/1024/1024),
			"percent": round(disk.percent,2),
		} if disk else None),
		"temperatures": temps,
		"gpus": gpus,
		"network": {"interfaces": interfaces},
	}


@app.get("/metrics/sys")
async def system_metrics():
	return build_system_metrics()

def build_remote_stub_metrics() -> Dict[str, Any]:
	return {
		"ts": int(time.time() * 1000),
		"host": "remote-ai-stub",
		"cpu": {"percent": None},
		"memory": {"percent": None},
		"gpus": [
			{"id": 0, "name": "RemoteGPU0", "load": None, "mem_used_mb": None, "mem_total_mb": None, "temperature": None},
			{"id": 1, "name": "RemoteGPU1", "load": None, "mem_used_mb": None, "mem_total_mb": None, "temperature": None},
		],
		"note": "Replace with real remote probe",
	}


@app.get("/metrics/remote_stub")
async def remote_stub_metrics():
	return build_remote_stub_metrics()


@app.websocket("/ws/metrics")
async def metrics_ws(ws: WebSocket, interval_ms: Optional[int] = 2000):
	await ws.accept()
	sleep_interval = max(250, min(10000, int(interval_ms or 2000))) / 1000.0
	try:
		while True:
			payload = {
				"system": build_system_metrics(),
				"remote": build_remote_stub_metrics(),
			}
			await ws.send_json(payload)
			await _ws_sleep(sleep_interval)
	except WebSocketDisconnect:
		return
	except Exception:
		# Attempt graceful close
		try:
			await ws.close()
		except Exception:
			pass


async def _ws_sleep(seconds: float):
	# Lightweight sleep to allow cancellation
	end = time.time() + seconds
	while time.time() < end:
		await asyncio.sleep(min(0.2, end - time.time()))

