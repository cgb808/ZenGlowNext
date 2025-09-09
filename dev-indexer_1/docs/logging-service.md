# Centralized gRPC Logging Service (Go)

This document captures the architectural shift from per-process CLI logging with filesystem locks to a single, highly concurrent Go-based gRPC logging service.

## Why this change

Before:
- Each agent/process wrote directly to the log file, coordinating via OS-level advisory locks (e.g., `fcntl`).
- This caused contention and context switching overhead across processes.

After:
- All agents send log frames to a central gRPC Log Service.
- The service manages file access internally. A dedicated goroutine per active log file serializes writes without cross-process locks.

Benefits:
- Lower contention, higher throughput, fewer syscalls.
- Cleaner API for producers and a single place to add rotation, compression, and shipping logic.

## gRPC Contract

Proto: `protos/services/logging/v1/logging.proto`

- Service: `logging.v1.LogService`
- Endpoint: `WriteLogStream` (client-streaming)
- Messages: `LogFrame`, `WriteLogResponse`

Key fields in `LogFrame`:
- `version` (int32)
- `time` (google.protobuf.Timestamp)
- `session_id`, `user_id`, `role` (strings)
- `seq` (int64; optional from client; service generates when missing)
- `content` (string)
- `metadata` (Struct)

## Concurrency Model

- A thread-safe map holds a channel per active session (log file).
- `WriteLogStream` pushes incoming frames to the corresponding channel.
- A long-lived goroutine (`sessionFileWriter`) owns the file handle and serializes all writes.
- This design eliminates file-lock thrashing across processes.

Pseudo-flow:
1. Client connects and streams `LogFrame` messages.
2. Server dispatches each frame to a session-specific channel.
3. The writer goroutine:
   - Allocates/increments a sequence number (if missing on input).
   - Appends to the current `.logtmp` file for that session.
   - Checks rotation criteria (size, age) and signals rotation when needed.
   - Performs periodic `fsync` or time-based flush for durability.

## Rotation & Compression

- Rotation triggers: max size, max age, idle timeout.
- On rotation request, the writer goroutine performs rename to a time/seq-stamped filename.
- Compression: offload to a separate worker goroutine (e.g., gzip), never blocking writes.
- Upload/queue: optionally publish a Redis message or enqueue a path for downstream processing.

Suggested env controls:
- `LOG_DIR` (default `./logs`)
- `LOG_MAX_SIZE_BYTES` (e.g., 64 MiB)
- `LOG_MAX_AGE_SECONDS` (e.g., 3600)
- `LOG_FLUSH_INTERVAL_MS` (e.g., 200)
- `LOG_COMPRESSION` (`gzip`/`none`)
- `REDIS_URL` (for optional queueing/events)

## Redis Integration (Optional)

- Publish rotation/completion events to Redis Pub/Sub or a list/stream for downstream ETL.
- Use `REDIS_PUBSUB_FORMAT=msgpack|json` to align with existing cache/transport conventions.
- Message schema can mirror `publish_build_update` style with `type`, `encoding`, `content`, and `timestamp`.

## Client Usage

1. Generate gRPC stubs from `protos/services/logging/v1/logging.proto`.
2. Agents open a client-streaming RPC and send `LogFrame` batches.
3. Keep streams alive per-session to minimize connection churn.
4. Allow the server to assign `seq` if you don’t track it client-side.

## Future Enhancements

- Backpressure: monitor channel depth; signal clients with `RESOURCE_EXHAUSTED` when overloaded.
- Hot session eviction: idle sessions close files and stop goroutines after a timeout.
- Durable queue: for crash resilience, append to a WAL or Redis stream before file write.
- Metrics: expose Prometheus counters for frames received, bytes written, rotations, errors.

## Status in Repo

- Proto added at `protos/services/logging/v1/logging.proto`.
- Go server scaffold recommended under `grpc-router/` (align with existing router). Implement a `logservice` module with:
  - session dispatcher (map[string]chan *LogFrame)
  - writer goroutine lifecycle (open/rotate/flush/close)
  - optional Redis notifier

See the existing caching patterns in `app/core/redis_cache.py` for compatible pub/sub envelopes.
