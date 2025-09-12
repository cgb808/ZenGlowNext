# DevOps TODO

Concise checklist to operationalize the ingestion pipeline and notifier.

## Build & bin placement

- [ ] Build notifier
  - `cd tools/notifier && go build -o ../../bin/notifier .`
- [ ] Ensure `bin/` is on PATH for services or reference full path in scripts.

## Spool directories & permissions

- [ ] Create spool dirs with correct ownership: incoming, processing, archive, failed
- [ ] Ensure service user can read/write these dirs
- [ ] Ensure log path exists (default `./logs/rag_ingestion.log` or `/var/log/rag_ingestion.log`)

## Environment wiring

- [ ] SPOOL_DIR, RAG_LOG_FILE
- [ ] DATABASE_URL (or SUPABASE_DB_URL) for manifest updates
- [ ] EMBED_BASE_URL if embedding is remote
- [ ] Notifier env for templates: GATE_URL, GATE_TOKEN
- [ ] Optional Redis env if also publishing to Redis

## Systemd integration

- [ ] Install watcher unit to trigger `scripts/process_spool.sh` on thresholds
- [ ] Add `Environment=` lines or an env file for SPOOL_DIR, thresholds, GATE_URL, etc.
- [ ] Start and enable the user service

## Security

- [ ] Lock down Postgres and Redis (TLS or private network)
- [ ] Gate URL must validate a token and rate-limit
- [ ] Avoid logging PII in orchestrator logs

## Observability

- [ ] Confirm NOTIFY or metrics on manifest updates
- [ ] Tail ingestion logs and set up rotation
- [ ] Secure failure log: any ingest/partition self-heal or permanent failure writes structured record to append-only log (owner root, 600)
- [ ] Dev dashboard alert: on first failure event (even if healed) emit alert with batch_tag, reason, healed=true/false
- [ ] Cron partition maintenance: capture run_maintenance() outcome + created partitions count; alert if zero created for >N intervals when expected
- [ ] gate.done reason codes documented (success, failed, healed_partition, partition_missing, other_error) and validated in notifier template test

## Tests

- [ ] Generate sample .msgpack files into incoming/
- [ ] Trigger watcher → process_spool.sh opens gate
- [ ] Verify gate.open notification delivered (check webhook logs)
- [ ] Verify database rows ingested
- [ ] Verify gate.done notification delivered
- [ ] Simulate partition missing -> self-heal retry path succeeds (expect healed_partition reason)
- [ ] Simulate persistent failure -> failure log + alert path exercised

## Redis Cache Wrapper (Planned)

- [ ] Implement class-based Redis client wrapper (`app/cache/redis_cache.py`) preserving legacy key pattern `rag:q:<sha1(query)>:<top_k>`
- [ ] Add namespaced helpers: `set_json_namespace(ns, key, value, ttl=None)` / `get_json_namespace(ns, key)`
- [ ] Add MessagePack variants; internal MD5 of (ns + key) for compact keys
- [ ] Integrate build update publisher (`publish_build_update`) emitting envelopes to channel `REDIS_BUILD_CHANNEL` (default `build_updates`)
- [ ] Environment variables documented & validated:
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL`
  - `DEFAULT_TTL_SECONDS` (fallback TTL)
  - `REDIS_BUILD_CHANNEL` (optional override)
- [ ] Add health probe to confirm connectivity & AUTH on startup
- [ ] Add unit tests: key hash stability, JSON round trip, MsgPack round trip, TTL expiry mock
- [ ] Add metrics increments (hits/misses) integrating with existing `cache_metrics`
- [ ] Update README + .env.example with new env vars
