# Development Knowledge Graph (DKG)

Purpose: Long-term, contextual memory layer to augment the RAG + ranking system with project mission, narrative decisions, and code structure intelligence.

---

## 1. Goals

- Capture WHY (missions, epics)
- Capture HOW (development_log: wins, losses, decisions, AI ↔ human interactions)
- Capture WHAT (source_documents + code_chunks with embeddings & metrics)
- Enable semantic + symbolic linking between narrative events and concrete code units.
- Provide substrate for: prompt grounding, regression detection, architectural drift alerts, roadmap summarization.

---

## 2. Schema Variants

| File                                                    | Description                                               |
| ------------------------------------------------------- | --------------------------------------------------------- |
| `sql/artifacts/dev_knowledge_graph_schema.sql`          | Namespaced version (`devkg` schema) – safer in shared DB. |
| `sql/artifacts/dev_knowledge_graph_schema_unscoped.sql` | Unscoped tables – only if isolation assured.              |

---

## 3. Core Entities

- `project_missions`: High-level objectives; status tracked.
- `project_epics`: Major feature tracks linked to missions.
- `development_log`: Canonical event stream (AI interactions, commits, decisions, bugs, perf tests) with optional outcome label.
- `source_documents`: One row per file, version + provenance.
- `code_chunks`: Fine-grained code units (function/class/region) with embeddings + analysis metrics.
- `log_to_chunk_link`: Many–many bridge tying events to affected code.
- `dev_model_registry`: Models used in tooling or generation (namespaced to avoid collision with production `model_registry`).
- `dev_query_performance`: Query telemetry over the DKG itself.

---

## 4. Indexing & Retrieval

- IVF Flat vector indexes (`*_embedding_idx`) support semantic similarity for narratives & code.
- Text + FK indexes accelerate epic and document scoping.
- Future: HNSW indexes if pgvector build supports; add composite (epic_id, occurred_at DESC) for time-window retrieval.

---

## 5. Example Use Cases

1. Prompt Augmentation: Pull last N `decision_log` + relevant `code_chunks` for a changed file, feed into model context.
2. Drift Detection: Periodically embed current code chunk; compare to prior versions; flag > threshold cosine shift.
3. Retrospective Generation: Query `development_log` for outcome='loss' to auto-summarize top failure themes.
4. Impact Trace: Given a function name, traverse `log_to_chunk_link` to surface related decisions & bug reports.
5. Experiment Memory: Store tuning outcomes as `performance_test` events and retrieve when similar change recurs.

---

## 6. Ingestion Workflow (Conceptual)

1. File Scan → hash diff → new / changed files upsert into `source_documents` (increment version if hash changed, mark previous version archived later).
2. Static Analysis Pass → extract functions/classes → compute embeddings + metrics → upsert `code_chunks`.
3. Event Logging API → append `development_log` rows with optional embedding (async job for embedding if large backlog).
4. Linking Step → auto-link commit / AI interaction to chunks touched (git diff + function spans).
5. Periodic Maintenance → re-embed stale (>30d) narratives; refresh vector indexes (ANALYZE).

---

## 7. Suggested APIs (Future)

- POST /dkg/event {event_type, title, narrative, metadata}
- POST /dkg/link {log_id, chunk_ids[]}
- GET /dkg/context?file_path=...&k=5 (returns recent related decisions + code chunk summaries)
- GET /dkg/search/narrative?q=... (semantic + keyword blend)
- GET /dkg/search/code?q=... (embedding + symbol filter)

---

## 8. Embedding Strategy

- Narrative & code both dimension 768 (align with existing RAG pipeline for potential cross-domain ANN).
- Consider separate normalization; maintain model version in `metadata.model_version` for re-embed migrations.
- Maintain a rolling queue for embedding updates; backpressure via batch size.

---

## 9. Quality & Governance

- Outcome labels enable automatic success/failure summarization.
- Enforce minimal narrative length (application layer) for better embeddings.
- Add data quality checks: null embeddings, stale analysis metrics, orphan links.

---

## 10. Future Extensions

- `architecture_components` table for higher-level system modules.
- `decision_vectors` materialized view clustering similar decisions.
- Temporal graph projection (events over dependency graph) for sequence modeling.
- Lightweight RL memory: reward shaping logs integrated with `development_log`.

---

## 11. Rollout Steps

1. Apply `dev_knowledge_graph_schema.sql` in staging.
2. Build ingestion job skeleton (file scanner + analyzer + event logger).
3. Add minimal API endpoints for event write + context fetch.
4. Pilot with automated capture of this assistant's summaries (convert to `ai_interaction`).
5. Evaluate retrieval quality; tune indexes (lists parameter) and re-embed frequency.

---

## 12. Ops Commands (Examples)

```sql
-- Reindex vector list parameter tweak
DROP INDEX IF EXISTS devkg.dev_log_embedding_idx;
CREATE INDEX dev_log_embedding_idx ON devkg.development_log USING ivfflat (narrative_embedding vector_cosine_ops) WITH (lists=150);

-- Backfill embeddings for narratives missing vectors
UPDATE devkg.development_log SET narrative_embedding = NULL WHERE narrative_embedding IS NULL; -- placeholder for embedding job
```

---

## 13. Open TODOs

- Decide retention for old code chunk versions (soft delete vs history table).
- Add outcome auto-classifier pipeline stub.
- Add composite index (event_type, occurred_at DESC) for timeline queries.
- Add embedding job spec & queue schema if needed.

---

## 14. References

- Internal: `docs/TASK_CHECKLIST.md` (Artifact A & future ingestion tasks)
- External: pgvector docs, software analytics research (code evolution metrics)
