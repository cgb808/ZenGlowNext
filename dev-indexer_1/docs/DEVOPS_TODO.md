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

## Tests

- [ ] Generate sample .msgpack files into incoming/
- [ ] Trigger watcher → process_spool.sh opens gate
- [ ] Verify gate.open notification delivered (check webhook logs)
- [ ] Verify database rows ingested
- [ ] Verify gate.done notification delivered
