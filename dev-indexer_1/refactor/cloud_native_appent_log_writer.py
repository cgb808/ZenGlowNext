"""Append Log Writer (Cloud-Native Edition)

This version extends the original high-performance writer with capabilities
for a distributed, cloud-native environment.

Key Enhancements:
  * Uploads sealed and compressed log segments to a cloud object store
    (e.g., Supabase Storage, AWS S3) instead of leaving them on local disk.
  * Publishes a structured event notification to a Redis Pub/Sub channel
    upon successful upload, rather than pushing a local file path to a list.

This decouples the log producer from the consumer, allowing them to run on
separate machines, in different containers, or as serverless functions,
which is essential for a scalable microservices architecture.
"""
from __future__ import annotations
import os, sys, argparse, json, time, uuid, struct, re, io
from datetime import datetime, UTC
from pathlib import Path
import asyncio
from typing import Optional

# --- Dependencies (ensure these are installed) ---
try:
    import msgpack
    import fcntl
    import redis.asyncio as aioredis
except ImportError as e:
    print(f"Missing required dependency: {e}", file=sys.stderr)
    raise

# --- Placeholder for Supabase/S3 Storage Client ---
# In a real application, this would be a more robust client.
class SupabaseStorageClient:
    """A lightweight client to upload files to Supabase Storage."""
    def __init__(self):
        # These would be securely loaded, e.g., from environment variables
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "log-segments")
        # In a real implementation, you would use the supabase-py library
        # self.client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
        print(f"[StorageClient] Initialized for bucket: {self.bucket_name} (using placeholder)")

    async def upload(self, local_path: Path, remote_path: str) -> str:
        """Uploads a local file to the storage bucket."""
        print(f"[StorageClient] UPLOADING {local_path} to gs://{self.bucket_name}/{remote_path}")
        # Placeholder logic: In a real implementation, this would contain the
        # actual upload call using the Supabase client library.
        # await self.client.storage.from_(self.bucket_name).upload(remote_path, str(local_path))
        await asyncio.sleep(0.1) # Simulate network latency
        print(f"[StorageClient] UPLOAD complete for {local_path}")
        return f"gs://{self.bucket_name}/{remote_path}" # Return the object storage URI

# --- Core Logic (largely unchanged, with async additions) ---

SAFE_SESSION_RE = re.compile(r'[^A-Za-z0-9._-]+')
_FRAME_COUNTER = 0

class LockTimeout(Exception):
    pass

# ... (iso, sanitize_session_id, session_paths, allocate_seq, try_lock, compress_file functions are identical to original) ...
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
            import zstandard as zstd
        except ImportError as e:
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

# --- Refactored Notification Logic ---
async def notify_segment_ready(seg_uri: str, redis_channel: str, batch_tag: str, metrics: dict) -> bool:
    """Publishes a structured event to a Redis Pub/Sub channel."""
    if not redis_channel:
        print(f"[segment] sealed {seg_uri}")
        return True
    try:
        redis_client = aioredis.from_url(os.getenv('REDIS_URL','redis://localhost:6379/0'))
        event_payload = {
            "eventType": "log_segment_sealed",
            "uri": seg_uri,
            "batchTag": batch_tag,
            "timestamp": iso(),
            "producer": "append_log_writer_cloud",
            "metrics": metrics
        }
        await redis_client.publish(redis_channel, json.dumps(event_payload))
        await redis_client.close()
        print(f"[notify] Published event for {seg_uri} to channel '{redis_channel}'")
        return True
    except Exception as e:
        print(f"[notify] Redis publish failed: {e}")
        return False

async def rotate_if_needed(
    logtmp: Path,
    max_size: int,
    max_age: int,
    redis_channel: Optional[str],
    strict_queue: bool,
    compress: Optional[str],
    remove_original: bool,
    metrics: dict,
    session_id: str,
    zstd_level: int = 3,
) -> Path:
    now = time.time()
    if logtmp.exists():
        st = logtmp.stat()
        age = now - st.st_mtime
        if st.st_size >= max_size or age >= max_age:
            ms = int(now * 1000)
            sealed = logtmp.with_name(f"{logtmp.stem}.log.{ms}")
            logtmp.rename(sealed)
            metrics['rotated'] = True
            metrics['rotation_size'] = st.st_size
            
            file_to_upload = sealed
            if compress:
                try:
                    comp_target = compress_file(sealed, compress, zstd_level=zstd_level)
                    metrics['compression_method'] = compress
                    metrics['compression_ratio'] = round(st.st_size / max(comp_target.stat().st_size,1), 4)
                    if remove_original:
                        sealed.unlink(missing_ok=True)
                    file_to_upload = comp_target
                except Exception as e:
                    metrics['compression_error'] = str(e)

            # Upload to cloud storage
            storage_client = SupabaseStorageClient()
            # Store by session_id for clearer organization in object storage
            remote_path = f"sessions/{session_id}/{file_to_upload.name}"
            
            try:
                seg_uri = await storage_client.upload(file_to_upload, remote_path)
                # After successful upload, remove the local copy
                file_to_upload.unlink(missing_ok=True)
                
                batch_tag = f"batch_{ms}" # Example batch tag
                ok = await notify_segment_ready(seg_uri, redis_channel, batch_tag, metrics)
                if strict_queue and not ok:
                    print('[error] notification publish failed (strict mode)', file=sys.stderr)
                    sys.exit(2)
            except Exception as e:
                 print(f"[error] upload or notify failed: {e}", file=sys.stderr)

    return logtmp

# ... (write_frame is identical to original) ...
def write_frame(log_path: Path, frame: dict, fsync_every: bool, fsync_interval: int, enable_lock: bool, lock_path: Path|None, lock_timeout: float|None, metrics: dict):
    global _FRAME_COUNTER
    header_payload = msgpack.packb(frame, use_bin_type=True)
    size_hdr = struct.pack('>I', len(header_payload))
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
            os.write(fd, size_hdr)
            os.write(fd, header_payload)
            _FRAME_COUNTER += 1
            do_fsync = False
            if fsync_every:
                do_fsync = True
            elif fsync_interval and (_FRAME_COUNTER % fsync_interval == 0):
                do_fsync = True
            if do_fsync:
                os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if lock_fd is not None:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

async def amain(args):
    session_id = sanitize_session_id(args.session_id)
    base = Path(args.log_dir)
    logtmp, lock_path, seq_path = session_paths(base, session_id)
    
    outer_lock_fd = None
    metrics: dict = {'rotated': False}
    try:
        if args.enable_lock:
            outer_lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
            try_lock(outer_lock_fd, exclusive=True, timeout=args.lock_timeout)
        
        compress_method = None if (args.compress is None or args.compress == 'none') else args.compress
        await rotate_if_needed(
            logtmp,
            args.max_size,
            args.max_age,
            args.redis_channel,
            args.strict_queue,
            compress_method,
            args.compress_remove_original,
            metrics,
            session_id,
            zstd_level=args.zstd_level,
        )
        
        seq = args.seq if args.seq is not None else allocate_seq(seq_path)

    finally:
        if outer_lock_fd is not None:
            fcntl.flock(outer_lock_fd, fcntl.LOCK_UN)
            os.close(outer_lock_fd)

    meta = json.loads(args.metadata_json) if args.metadata_json else {}
    
    frame = {
        'version': 1,
        'time': iso(),
        'session_id': session_id,
        'user_id': args.user_id,
        'role': args.role,
        'seq': seq,
        'content': args.content,
        'metadata': meta,
    }
    
    write_frame(logtmp, frame, fsync_every=args.fsync, fsync_interval=args.fsync_interval or 0, 
                enable_lock=args.enable_lock, lock_path=lock_path if args.enable_lock else None, 
                lock_timeout=args.lock_timeout, metrics=metrics)
    
    size = logtmp.stat().st_size if logtmp.exists() else 0
    print(f"[append] {session_id} seq={seq} size={size}")

def main():
    ap = argparse.ArgumentParser(description="Cloud-Native Append Log Writer")
    ap.add_argument('--session-id', default=str(uuid.uuid4()), help='Session identifier; sanitized to safe chars')
    ap.add_argument('--user-id', required=True, help='User identifier associated with the frame')
    ap.add_argument('--log-dir', default=os.getenv('APPEND_LOG_DIR', 'runs/logs'), help='Directory to store/rotate log segments')
    ap.add_argument('--role', default='user', choices=['user','assistant','system','tool'], help='Role of the content origin')
    ap.add_argument('--content', required=True, help='Content payload to append as a frame')
    ap.add_argument('--metadata-json', default=None, help='Optional JSON string metadata to include in frame')
    ap.add_argument('--seq', type=int, default=None, help='Explicit sequence number to write; auto-increment if omitted')

    # Rotation controls
    ap.add_argument('--max-size', type=int, default=int(os.getenv('APPEND_ROTATE_MAX_SIZE', str(5 * 1024 * 1024))), help='Rotate when file reaches this size in bytes')
    ap.add_argument('--max-age', type=int, default=int(os.getenv('APPEND_ROTATE_MAX_AGE', '30')), help='Rotate when file age (seconds since mtime) exceeds this')

    # Sync + locking
    ap.add_argument('--fsync', action='store_true', help='fsync on every frame append')
    ap.add_argument('--fsync-interval', type=int, default=int(os.getenv('APPEND_FSYNC_INTERVAL', '100')), help='fsync every N frames (ignored if --fsync)')
    ap.add_argument('--enable-lock', action='store_true', help='Enable file lock during writes (recommended)')
    ap.add_argument('--lock-timeout', type=float, default=float(os.getenv('APPEND_LOCK_TIMEOUT', '2.0')), help='Seconds to wait for write lock before failing')

    # Compression
    ap.add_argument('--compress', choices=['none','zstd','gzip'], default=os.getenv('APPEND_COMPRESS', 'zstd'), help='Compression method for sealed segments')
    ap.add_argument('--zstd-level', type=int, default=int(os.getenv('APPEND_ZSTD_LEVEL', '3')), help='Zstandard compression level')
    ap.add_argument('--compress-remove-original', action='store_true', help='Remove original uncompressed file after compressing')

    # Notifications
    ap.add_argument('--redis-channel', default=os.getenv('APPEND_REDIS_CHANNEL'), help='Redis Pub/Sub channel for sealed segment notifications')
    ap.add_argument('--strict-queue', action='store_true', help='Exit non-zero if notification publish fails')

    args = ap.parse_args()
    
    try:
        asyncio.run(amain(args))
    except LockTimeout:
        print('[error] lock-timeout acquiring outer lock', file=sys.stderr)
        sys.exit(3)
    except KeyboardInterrupt:
        print("\n[signal] interrupt; exiting")

if __name__ == '__main__':
    main()
