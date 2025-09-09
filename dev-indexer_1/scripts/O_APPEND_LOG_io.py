#!/usr/bin/env python3
"""Append Log Writer (O_APPEND + Advisory Locking + Atomic Sequence + Optional Compression + Metrics)

Features vs original append_log_writer:
  * Optional per-session advisory lock (--enable-lock) using flock on a .lock file
	to make rotation + write atomic across processes.
  * Atomic sequence allocation via per-session .seq file (no need to scan log).
  * O_APPEND writes with os.write to reduce race risk without full-file reads.
  * Configurable durability: --fsync (every frame) or --fsync-interval N (every N frames).
	* Optional compression of sealed segments on rotation (--compress zstd|gzip, with removal flag).
	* Lock acquisition timeout (--lock-timeout) to avoid indefinite blocking.
	* Lightweight metrics emission (--emit-metrics JSON line to stdout; optional --metrics-file append JSONL).
  * Reuses safe session id sanitization.

Frame schema:
  {
	"version":1,
	"time": iso8601,
	"session_id": str,
	"user_id": str,
	"role": str,
	"seq": int,
	"content": str,
	"metadata": {...}
  }

Rotation: size or age triggers rename of *.logtmp -> *.log then queue segment path
		  via Redis list (if --redis-list provided) or stdout fallback.

NOTE: fsync interval counter is per-process and not shared. Multiple writers
	  each have their own interval schedule.
"""
from __future__ import annotations
import os, sys, argparse, json, time, uuid, struct, re
from datetime import datetime, UTC
from pathlib import Path

try:
	import msgpack  # type: ignore
except Exception as e:  # noqa: BLE001
	print("msgpack required", e, file=sys.stderr); raise

try:
	import fcntl  # type: ignore
except Exception as e:  # noqa: BLE001
	print("fcntl module required on POSIX systems", e, file=sys.stderr); raise

SAFE_SESSION_RE = re.compile(r'[^A-Za-z0-9._-]+')

# In-memory frame counter (per process)
_FRAME_COUNTER = 0

class LockTimeout(Exception):
	pass

def iso() -> str:
	return datetime.now(UTC).isoformat()

def sanitize_session_id(raw: str) -> str:
	cleaned = SAFE_SESSION_RE.sub('-', raw).strip('-') or 'session'
	return cleaned[:120]

def session_paths(base: Path, session_id: str):
	base.mkdir(parents=True, exist_ok=True)
	logtmp = base / f"session_{session_id}.logtmp"
	lock = base / f"session_{session_id}.lock"
	seq = base / f"session_{session_id}.seq"
	return logtmp, lock, seq

def allocate_seq(seq_path: Path) -> int:
	fd = os.open(seq_path, os.O_CREAT | os.O_RDWR, 0o600)
	try:
		fcntl.flock(fd, fcntl.LOCK_EX)
		os.lseek(fd, 0, os.SEEK_SET)
		data = os.read(fd, 64)
		try:
			last = int(data.decode().strip()) if data else -1
		except Exception:
			last = -1
		new = last + 1
		os.lseek(fd, 0, os.SEEK_SET)
		os.ftruncate(fd, 0)
		os.write(fd, f"{new}\n".encode())
		os.fsync(fd)
		return new
	finally:
		fcntl.flock(fd, fcntl.LOCK_UN)
		os.close(fd)

def try_lock(fd: int, exclusive=True, timeout: float|None=None, poll_interval: float=0.05):
	mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
	end: float = time.time() + timeout if timeout is not None else 0.0
	while True:
		try:
			fcntl.flock(fd, mode | (fcntl.LOCK_NB if timeout is not None else 0))
			return
		except BlockingIOError:
			if timeout is not None and time.time() >= end:
				raise LockTimeout()
			time.sleep(poll_interval)

def compress_file(path: Path, method: str, zstd_level: int = 3) -> Path:
	if method == 'zstd':
		try:
			import zstandard as zstd  # type: ignore
		except Exception as e:  # noqa: BLE001
			print(f"[compress] zstd unavailable: {e}")
			raise
		tgt = path.with_suffix(path.suffix + '.zst')
		c = zstd.ZstdCompressor(level=zstd_level)
		with path.open('rb') as src, tgt.open('wb') as dst:
			c.copy_stream(src, dst)
		return tgt
	elif method == 'gzip':
		import gzip
		tgt = path.with_suffix(path.suffix + '.gz')
		with path.open('rb') as src, gzip.open(tgt, 'wb') as dst:
			while True:
				chunk = src.read(65536)
				if not chunk:
					break
				dst.write(chunk)
		return tgt
	else:
		raise ValueError(f"unknown compression method {method}")

def queue_segment(seg: Path, redis_list: str|None, redis_ttl: int = 0) -> bool:
	if redis_list:
		try:
			import redis  # type: ignore
			r = redis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0'))
			r.lpush(redis_list, str(seg))
			if redis_ttl and redis_ttl > 0:
				try:
					r.expire(redis_list, int(redis_ttl))
				except Exception:
					pass
			print(f"[queue] {seg} -> {redis_list}")
			return True
		except Exception as e:  # noqa: BLE001
			print(f"[queue] redis fail: {e}")
			return False
	print(f"[segment] sealed {seg}")
	return True

def rotate_if_needed(logtmp: Path, max_size: int, max_age: int, redis_list: str|None, strict_queue: bool, compress: str|None, remove_original: bool, metrics: dict, zstd_level: int = 3, redis_ttl: int = 0) -> Path:
	now = time.time()
	if logtmp.exists():
		st = logtmp.stat()
		age = now - st.st_mtime
		if st.st_size >= max_size or age >= max_age:
			# Unique sealed name to avoid overwriting: session_<id>.log.<epoch_ms>
			ms = int(now * 1000)
			sealed = logtmp.with_name(f"{logtmp.stem}.log.{ms}")
			logtmp.rename(sealed)
			metrics['rotated'] = True
			metrics['rotation_size'] = st.st_size
			metrics['rotation_age'] = round(age, 3)
			comp_target = None
			if compress:
				comp_start = time.time()
				try:
					comp_target = compress_file(sealed, compress, zstd_level=zstd_level)
					metrics['compression_method'] = compress
					metrics['compression_ratio'] = round(st.st_size / max(comp_target.stat().st_size,1), 4)
					metrics['compression_ms'] = int((time.time()-comp_start)*1000)
					if remove_original:
						sealed.unlink(missing_ok=True)  # type: ignore[arg-type]
						metrics['removed_original_after_compress'] = True
					# queue compressed variant path instead
					ok = queue_segment(comp_target, redis_list, redis_ttl)
				except Exception as e:  # noqa: BLE001
					metrics['compression_error'] = str(e)
					ok = queue_segment(sealed, redis_list, redis_ttl)
			else:
				ok = queue_segment(sealed, redis_list, redis_ttl)
			if strict_queue and not ok:
				print('[error] queue push failed (strict mode)', file=sys.stderr)
				sys.exit(2)
	# return (possibly newly created) logtmp path
	return logtmp

def write_frame(log_path: Path, frame: dict, fsync_every: bool, fsync_interval: int, enable_lock: bool, lock_path: Path|None, lock_timeout: float|None, metrics: dict):
	global _FRAME_COUNTER
	header_payload: bytes = msgpack.packb(frame, use_bin_type=True)  # type: ignore[assignment]
	size_hdr = struct.pack('>I', len(header_payload))
	# Acquire lock if requested
	lock_fd = None
	try:
		if enable_lock and lock_path is not None:
			lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
			t0 = time.time()
			try:
				try_lock(lock_fd, exclusive=True, timeout=lock_timeout)
			except LockTimeout:
				raise SystemExit(3)
			metrics['write_lock_ms'] = int((time.time()-t0)*1000)
		fd = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
		try:
			t_write_start = time.time()
			os.write(fd, size_hdr)
			os.write(fd, header_payload)
			_FRAME_COUNTER += 1
			do_fsync = False
			if fsync_every:
				do_fsync = True
			elif fsync_interval and (_FRAME_COUNTER % fsync_interval == 0):
				do_fsync = True
			if do_fsync:
				fs0 = time.time()
				os.fsync(fd)
				metrics['fsync_ms'] = int((time.time()-fs0)*1000)
			metrics['bytes_written'] = len(size_hdr) + len(header_payload)
			metrics['write_ms'] = int((time.time()-t_write_start)*1000)
		finally:
			os.close(fd)
	finally:
		if lock_fd is not None:
			fcntl.flock(lock_fd, fcntl.LOCK_UN)
			os.close(lock_fd)

def main():
	ap = argparse.ArgumentParser(description="O_APPEND append log writer with locking & atomic seq")
	ap.add_argument('--session-id', default=str(uuid.uuid4()))
	ap.add_argument('--user-id', required=True)
	ap.add_argument('--role', default='user')
	ap.add_argument('--content', required=True)
	ap.add_argument('--log-dir', default='data/append_logs')
	ap.add_argument('--max-size', type=int, default=64*1024*1024)
	ap.add_argument('--max-age', type=int, default=600)
	ap.add_argument('--redis-list')
	ap.add_argument('--metadata-json')
	ap.add_argument('--seq', type=int, help='Override sequence (skip allocator)')
	ap.add_argument('--enable-lock', action='store_true')
	ap.add_argument('--strict-queue', action='store_true')
	ap.add_argument('--fsync', action='store_true', help='fsync each frame')
	ap.add_argument('--fsync-interval', type=int, help='fsync every N frames (per process)')
	ap.add_argument('--compress', choices=['zstd','gzip'], help='Compress sealed segments on rotation')
	ap.add_argument('--zstd-level', type=int, default=3, help='zstd compression level (if --compress zstd)')
	ap.add_argument('--compress-remove-original', action='store_true')
	ap.add_argument('--lock-timeout', type=float, help='Seconds before giving up on acquiring outer advisory lock')
	ap.add_argument('--emit-metrics', action='store_true', help='Emit metrics JSON line to stdout')
	ap.add_argument('--metrics-file', help='Append metrics JSON to file (JSONL)')
	ap.add_argument('--redis-ttl-seconds', type=int, default=0, help='Set TTL on Redis list after push (0=disabled)')
	args = ap.parse_args()

	session_id = sanitize_session_id(args.session_id)
	base = Path(args.log_dir)
	logtmp, lock_path, seq_path = session_paths(base, session_id)

	# Lock (if enabled) around rotation decision + sequence allocation + write for strong safety
	outer_lock_fd = None
	metrics: dict = {'rotated': False}
	try:
		if args.enable_lock:
			outer_lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
			t0 = time.time()
			try:
				try_lock(outer_lock_fd, exclusive=True, timeout=args.lock_timeout)
			except LockTimeout:
				print('[error] lock-timeout acquiring outer lock', file=sys.stderr)
				sys.exit(3)
			metrics['outer_lock_ms'] = int((time.time()-t0)*1000)
		# rotation check inside lock
		rotate_if_needed(
			logtmp,
			args.max_size,
			args.max_age,
			args.redis_list,
			args.strict_queue,
			args.compress,
			args.compress_remove_original,
			metrics,
			zstd_level=args.zstd_level,
			redis_ttl=args.redis_ttl_seconds,
		)
		# sequence
		if args.seq is not None:
			seq = args.seq
		else:
			seq = allocate_seq(seq_path)
	finally:
		if outer_lock_fd is not None:
			fcntl.flock(outer_lock_fd, fcntl.LOCK_UN)
			os.close(outer_lock_fd)

	# metadata parse (outside heavy lock to minimize contention)
	if args.metadata_json:
		try:
			meta = json.loads(args.metadata_json)
			if not isinstance(meta, dict):
				raise ValueError('metadata must be object')
		except Exception as e:  # noqa: BLE001
			print(f"[warn] bad metadata JSON: {e}; using empty object")
			meta = {}
	else:
		meta = {}

	frame = {
		'version':1,
		'time': iso(),
		'session_id': session_id,
		'user_id': args.user_id,
		'role': args.role,
		'seq': seq,
		'content': args.content,
		'metadata': meta,
	}
	write_frame(logtmp, frame, fsync_every=args.fsync, fsync_interval=args.fsync_interval or 0, enable_lock=args.enable_lock, lock_path=lock_path if args.enable_lock else None, lock_timeout=args.lock_timeout, metrics=metrics)
	size = logtmp.stat().st_size if logtmp.exists() else 0
	print(f"[append] {session_id} seq={seq} size={size} fsync={'yes' if args.fsync else ('interval' if args.fsync_interval else 'no')} rotated={metrics['rotated']}")
	if args.emit_metrics or args.metrics_file:
		metrics.update({'session_id': session_id, 'seq': seq, 'size_after': size, 'fsync_mode': ('every' if args.fsync else ('interval' if args.fsync_interval else 'none'))})
		line = json.dumps({'type': 'append_log_metrics', **metrics}, ensure_ascii=False)
		if args.emit_metrics:
			print(line)
		if args.metrics_file:
			try:
				with open(args.metrics_file, 'a', encoding='utf-8') as mf:
					mf.write(line + '\n')
			except Exception as e:  # noqa: BLE001
				print(f"[warn] failed writing metrics file: {e}")

if __name__ == '__main__':
	main()

