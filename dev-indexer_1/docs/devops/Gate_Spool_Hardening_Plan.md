# Gate & Spool Hardening (Deferred Design)

Status: Draft / Not Implemented
Decision: Parked until real-world throughput + failure modes observed.

## Purpose
Capture the proposed architecture for future hardening of ingestion + routing without prematurely over-engineering. This document SHOULD NOT drive immediate implementation.

## Triggers to Revisit
- Sustained ingest > 2k docs/min OR burst > 10k in <2 min.
- Any data loss event during crash / restart.
- Embedding latency p95 > target for 3 consecutive days.
- Need for multi-host redundancy / blue-green failover.

## Summary of Deferred Features
| Feature | Rationale | Deferral Risk |
|---------|-----------|--------------|
| Local durable spool (segment log) | Crash recovery, replay | Possible data loss on process crash now (accept) |
| Slot-based ownership & redundancy | Predictable partition, limited blast radius | Uneven load after scale-out |
| Multi-role container supervisor | Single image, shared model memory | Extra process complexity |
| Redis stream integration (XADD) | Durable cross-node queue | Adds ops overhead early |
| Envelope v1 msgpack schema | Standard interchange w/ future Go gate | Slight migration cost later |
| Idempotent re-emit + tombstones | Duplicate avoidance on replay | Occasional double-processing risk now |
| Backpressure & priority lanes | Stabilize during burst | Latency spikes under burst |
| Metrics: spool depths, lag, replay counters | SLO enforcement | Blind to buildup |

## Simplified Current Path (Accepted)
```
Ingest -> (memory queue) -> embedding worker -> DB / vector store
```
Assumptions accepted short-term:
- Memory queue loss acceptable (dev / early stage).
- Single process crash recovery = manual reingest if needed.
- Throughput modest; disk durability premature.

## Deferred Future Path (Conceptual)
```
Ingest -> L1 Spool (fs segment append) -> Mem ring -> Gate classify/tag -> Envelope (msgpack)
        -> Embed consumer -> Vector store + metadata -> Index writer ack -> Tombstone
```
Optional L2: Redis Stream (multi-node).

## Envelope (Draft v1)
```
{
  id, source, text_hash, char_len,
  pii{}, tags[], intent_hint, routing_hints{}, summary_extractive,
  embed_preview?, embed_ref?, version, ts_ms, meta{}
}
```
Evolution: add slot, takeover flags when swarm introduced.

## Slot / Redundancy (Draft)
- TOTAL_SLOTS = power-of-two (e.g., 1024)
- Replication factor R=2 (primary, secondary)
- Hash(id) % TOTAL_SLOTS -> slot
- Ownership map maintained in Redis (future) or static config early.

## Failure Handling (Target Behavior)
| Stage | Failure | Desired Outcome |
|-------|---------|-----------------|
| Gate process crash | Pending envelopes remain on disk | Replay on restart |
| Embed worker crash | Unembedded envelopes retained | Another worker picks up |
| Primary slot owner lost | Secondary promotes | Minimal gap |
| Disk near full | Backpressure triggers (429 / pause) | Prevent total failure |

## Metrics (Future)
- spool_pending_total
- spool_segments_active
- spool_oldest_age_sec
- gate_envelopes_total
- embed_latency_ms (histogram)
- replay_recovered_total

## Implementation Phases (Deferred)
1. Shadow spool append only.
2. Replay + idempotent embedding.
3. Completion tombstones + compaction.
4. Slot ownership + failover.
5. Redis stream bridging.
6. Priority queues + backpressure.
7. Full metrics & dashboards.

## Open Questions
- Keep raw text in envelope or hash-only post-ingest? (privacy vs debug)
- When to introduce micro-embedding preview? (only if early filter ROI > 15% CPU save)
- Do we standardize on Redis Streams vs adopt NATS/Redpanda directly for L2?

## Exit Criteria For Hardening Kickoff
All of:
- Monitoring shows sustained > threshold throughput OR first data-loss incident.
- Basic observability (latencies, error counts) already stable.
- Product need for deterministic partition (SLO, latency isolation) documented.

---
Prepared for future activation; no runtime dependency today.
