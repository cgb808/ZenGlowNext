# Ingestion Spool Automation

This doc describes a resilient file-based ingestion pipeline using a spool directory, a wrapper script, and a filesystem watcher that triggers ingestion when enough data has arrived.

## Directory Structure

```
/data/spool/
├── incoming/      # Agents drop new .msgpack files here
├── processing/    # Files are moved here during the ingestion run
├── archive/       # Successfully processed files are moved here
└── failed/        # Files that cause an error are moved here for inspection
```

In this repo, we provide the structure under `data/spool/` for local dev. Adjust the absolute path in env if you mount a different volume in production.

## Wrapper Script: process_spool.sh

A shell orchestrator that atomically moves pending files, runs the ingestion tool, and archives or quarantines results.

- Reads configuration from env with sensible defaults.
- Uses `--skip-existing` for idempotency when replaying MessagePack artifacts.
- Logs to a file and stdout (safe to pipe into journald).

Path: `scripts/process_spool.sh`

## Watcher: spool_poll_watcher.py (stdlib)

A lightweight polling watcher (stdlib-only) checks `incoming/` on an interval and triggers `process_spool.sh` when thresholds are met.

- Thresholds: min bytes and/or min file count
- No third-party dependencies (works in minimal environments)
- Pair with systemd for boot-time start and automatic restarts

Path: `scripts/spool_poll_watcher.py`

## systemd Unit (template)

Path: `systemd/spool-watcher.service`

```
[Unit]
Description=Spool Directory Watcher for RAG Ingestion
After=network.target

[Service]
EnvironmentFile=/etc/default/zenglow-indexer  # optional env file
ExecStart=/usr/bin/python3 /opt/zenglow/scripts/spool_poll_watcher.py
WorkingDirectory=/opt/zenglow/scripts
StandardOutput=journal
StandardError=journal
Restart=always
User=zenglow

[Install]
WantedBy=multi-user.target
```

Then:

```
sudo systemctl daemon-reload
sudo systemctl enable spool-watcher.service
sudo systemctl start spool-watcher.service
```

## Environment Variables

Watcher (polling):

- `SPOOL_DIR` (default `/data/spool`)
- `SPOOL_MIN_BYTES` (default `4000000`)
- `SPOOL_MIN_FILES` (default `1`)
- `SPOOL_POLL_INTERVAL` (default `5` seconds)
- `SPOOL_PROCESS_SCRIPT` (optional path to `process_spool.sh`)

Orchestrator (`process_spool.sh`):

- `SPOOL_DIR` (default `./data/spool`)
- `PYTHON_REPLAY_SCRIPT` (default `./scripts/rag_replay_msgpack.py`)
- `RAG_LOG_FILE` (default `./logs/rag_ingestion.log`)
- `DATABASE_URL` or `SUPABASE_DB_URL` for manifest updates
- Optional notifier:
	- `NOTIFIER_BIN` (default `./bin/notifier`)
	- `NOTIFIER_TPL_OPEN` (default `./tools/notifier/templates/gate_open.json.tmpl`)
	- `NOTIFIER_TPL_DONE` (default `./tools/notifier/templates/gate_done.json.tmpl`)
	- Template envs: `GATE_URL`, `GATE_TOKEN`
 - Optional PII gate (PII DB):
	 - `PII_DATABASE_URL` (required to enable)
	 - `PII_GATE` (default `1` → enabled)
	 - `PII_GATE_HELPER` (default `./scripts/pii_gate.py`)

## Notes

- The polling watcher has no external deps. If you prefer events, add a watchdog variant.
- The ingestion tool expects `DATABASE_URL`/`SUPABASE_DB_URL` and optionally `EMBED_BASE_URL`.
- For production, point `SPOOL_DIR` to a durable volume (e.g., ZFS) and rotate logs.
- The notifier is optional; when present, it sends gate.open and gate.done events to your webhook.
- Optional PII Gate: the orchestrator creates a locked gate row per batch in the PII DB and opens it only after successful ingest. Other services can poll `scripts/pii_gate.py wait --batch-tag TAG` before proceeding with PII-dependent work.
