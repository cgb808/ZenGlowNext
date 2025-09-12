## Ingestion Notifier: Events, Channels, and Contract

This document defines the publish contract used to signal ingest lifecycle and to kick off embedding. It targets a Supabase Edge Function that relays messages to Redis.

### Overview

- Transport: HTTPS to Supabase Edge Function (you host) → Redis Pub/Sub
- Producer: Orchestrator `scripts/process_spool.sh` via Go notifier `tools/notifier`
- Consumers: Agents/services subscribed to Redis channels (see below)
- Delivery: Fire-and-forget, at-least once; notifier fails on non-2xx (configurable)

### Edge Function HTTP Contract

Request body sent to the Edge Function:

```
{ "action": "publish", "channel": string, "message": string }
```

- `channel`: Redis channel to publish to
- `message`: STRING payload. The value is a JSON-encoded string; subscribers should parse it as JSON.

Auth: Bearer token in `Authorization: Bearer <EDGE_TOKEN>` header.
Endpoint: Prefer `event-publish` function for validation/persistence.

### Channels and Events

1) Gate open (before replay)
- Channel: `ingest_updates`
- Message JSON (string):
```
{"event":"gate.open","batch_tag":"<tag>","spool":"<abs_spool_processing_dir>","bytes":<N>,"count":<M>,"pii":false,"ts":<UNIX_EPOCH_S>}
```

2) Gate done (after replay)
- Channel: `ingest_updates`
- Message JSON (string):
```
{"event":"gate.done","batch_tag":"<tag>","status":"success|failed","processed":<N>,"pii":false,"ts":<UNIX_EPOCH_S>}
```

3) Start embedding (after success)
- Channel: `embed_updates`
- Message JSON (string):
```
{"event":"embed.start","batch_tag":"<tag>","pii":false,"ts":<UNIX_EPOCH_S>}
```

Notes:
- `batch_tag` is stable across events for the same ingest run.
- `ts` is Unix epoch seconds. For backfills, you may pass a historical `ts`; if omitted, templates default to current epoch via `epoch`. The Edge `event-publish` function will persist the provided `ts`.
 - `pii` is a boolean; default false. Mark true if the batch may contain PII so subscribers can gate or route appropriately. Persisted in `ingest_events` and mirrored in external TS when configured.

### Templates and Locations

- Go notifier CLI: `tools/notifier` (build to `bin/notifier`)
- Templates (Go text/template → JSON):
  - `tools/notifier/templates/gate_open.json.tmpl`
  - `tools/notifier/templates/gate_done.json.tmpl`
  - `tools/notifier/templates/embed_start.json.tmpl`

Template helpers available:
- `env "VAR"` reads environment variables
- `epoch` renders current Unix seconds
- `now` (time.Time) and `join` are also available
- `coalesce` picks the first non-empty value, e.g. `{{ coalesce .ts (epoch) }}` to support historical timestamps on backfill.

### Orchestrator Hooks

`scripts/process_spool.sh` wires the lifecycle:
- On gate open (before replay): renders `gate_open.json.tmpl`
- On success: renders `gate_done.json.tmpl` with status `success` and then `embed_start.json.tmpl`
- On failure: renders `gate_done.json.tmpl` with status `failed`

The orchestrator builds template data using Python stdlib JSON (no jq dependency).

Env overrides used by the orchestrator:
- `NOTIFIER_BIN` (default `./bin/notifier`)
- `NOTIFIER_TPL_OPEN` (default `./tools/notifier/templates/gate_open.json.tmpl`)
- `NOTIFIER_TPL_DONE` (default `./tools/notifier/templates/gate_done.json.tmpl`)
- `NOTIFIER_TPL_EMBED_START` (default `./tools/notifier/templates/embed_start.json.tmpl`)

### Notifier HTTP Target Env

Set these where the orchestrator runs (shell or systemd EnvironmentFile):
- `EDGE_URL`: `https://<project>.functions.supabase.co/event-publish`
- `EDGE_TOKEN`: Supabase service key (or anon, if permitted)

Optional observability:
- Set `TIMESERIES_WEBHOOK_URL` in `event-publish` env to mirror a tiny record to an external TS store.

### Minimal Subscriber Examples

Python (redis-py):
```
import json, os, redis
r = redis.Redis(host=os.getenv('REDIS_HOST','localhost'), port=int(os.getenv('REDIS_PORT','6379')), db=int(os.getenv('REDIS_DB','0')), password=os.getenv('REDIS_PASSWORD'))
ps = r.pubsub(); ps.subscribe('ingest_updates', 'embed_updates')
for m in ps.listen():
    if m['type'] != 'message':
        continue
    evt = json.loads(m['data'])  # message is a JSON string
    print('chan=', m['channel'], 'evt=', evt)
```

Node (ioredis):
```
import Redis from 'ioredis'
const sub = new Redis(process.env.REDIS_URL)
await sub.subscribe('ingest_updates', 'embed_updates')
sub.on('message', (channel, message) => {
  const evt = JSON.parse(message)
  console.log(channel, evt)
})
```

### Fine-tuning reference (gate event forms)

See `datasets/fine_tuning/ingest_events_gate_tuning.jsonl` for compact examples of properly formed `gate.open`, `gate.done`, and `embed.start` payloads including `pii` and `ts` usage (current vs historical).

### Reliability and Semantics

- Delivery: at-least-once. The notifier exits non-zero on non-2xx by default; orchestrator does not retry by itself.
- Recommended: consumers should de-duplicate by `(event, batch_tag)` and treat `embed.start` as idempotent.
- Failure surfaces: network errors, 4xx/5xx from Edge Function; notifier logs to stderr and returns non-zero if `-require-2xx` is true (default).

### Downstream Go Services (Context)

Recent Go components consume or can be extended to react to these events:

- `cmd/ingester/` (gRPC streaming ingestion scaffold): After a successful `gate.done (success)` the `embed.start` event is a natural hook to trigger deferred embedding, dedupe, or COPY-batch inserts once embeddings are ready. The ingester currently provides a streaming RPC stub; wire a Redis subscriber to push ready records into the service.
- `internal/canonical` (TopK query / semantic retrieval stub): Can index or refresh lightweight caches after `embed.start` batches finish embedding. Use the shared `batch_tag` to correlate.
- `grpc-router` service: May route specialized downstream processing (e.g., classification) based on channel (`ingest_updates` vs `embed_updates`).

Integration pattern:
1. Subscribe to `ingest_updates` & `embed_updates`.
2. Maintain an in-memory map keyed by `batch_tag` capturing `gate.open` metadata (bytes/count, pii).
3. On `gate.done success`, schedule embedding (if not already enqueued) then emit internal jobs for the ingester.
4. On `embed.start`, update status → "embedding" and optionally notify the canonical service to anticipate new vectors.

These additions keep the notifier contract stable while allowing newer Go services to remain decoupled and event-driven.

### Security

- Use a service key for production; restrict the Edge Function to `action === 'publish'` and allowlisted channels only.
- Validate `message` size and optionally schema to avoid abuse.
- Require HTTPS and validate token; rotate tokens regularly.

### Quick Test

1) Build notifier:
```
cd tools/notifier && go build -o ../../bin/notifier .
```
2) Dry send an open event (replace values):
```
GATE_URL=... GATE_TOKEN=... \
  ./bin/notifier -template tools/notifier/templates/gate_open.json.tmpl \
  -data '{"batch_tag":"spool_20250909_101010","spool":"/data/spool/processing","bytes":12345,"count":2}' -v
```

If your Edge Function is wired, subscribers on `ingest_updates` should receive the parsed JSON payload as a string.
