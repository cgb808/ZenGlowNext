## Ingest/Embed Event Dataset Builder (for fine-tune)

This guide and schemas help you construct a clean dataset around the ingest lifecycle and embedding triggers, including PII gating tags and channel policies.

### Schemas

- Edge Function request: `schemas/edge_publish_request.schema.json`
- Ingest events (payloads on Redis): `schemas/ingest_events.schema.json`
- PII gate & publish policy: `schemas/pii_gate_policy.schema.json`

### Recommended dataset shape (JSONL)

Each line is one training sample:

```
{
  "channel": "ingest_updates",
  "message": {"event":"gate.open","batch_tag":"spool_20250909_101010","spool":"/data/spool/processing","bytes":123456,"count":2,"ts":1694265600},
  "policy": {"pii_allowed": false, "max_message_bytes": 32768},
  "labels": {"pii": false, "action": "ack"}
}
```

Fields:
- `channel`: where the event was published
- `message`: parsed JSON payload (must validate against `ingest_events.schema.json`)
- `policy`: snapshot of the channel policy when labeling
- `labels`:
  - `pii`: whether the payload contains PII (for gating)
  - `action`: classifier outcome e.g., `ack`, `retry`, `drop`, `defer`

### Example JSONL (starter)

See `datasets/examples/ingest_events_sample.jsonl`.

### Building a set

1) Collect events from Redis subscriptions or logs.
2) Validate messages against `schemas/ingest_events.schema.json`.
3) Join with your `pii_gate_policy` snapshot for the channel.
4) Annotate `labels.pii` (true/false) and `labels.action`.
5) Export to JSONL for fine-tuning or training your agent.

### PII tagging guidance

- Do not include raw PII in the dataset; replace with placeholders or tokens.
- Use deterministic tokens (e.g., `{{PHONE}}`, `{{EMAIL}}`) when needed for context.
- Maintain a mapping only in secure environments; do not ship mappings.
