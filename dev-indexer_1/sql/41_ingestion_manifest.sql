-- =============================================================
-- Schema: Ingestion Manifest & Real-time Notifier
-- Purpose: To track the lifecycle of data ingestion batches.
-- =============================================================
-- Minimal ingestion manifest table to track spool batches
CREATE TABLE IF NOT EXISTS ingestion_manifest (
    id BIGSERIAL PRIMARY KEY,
    batch_tag TEXT NOT NULL UNIQUE,          -- A unique name for the batch
    status TEXT NOT NULL DEFAULT 'queued',   -- Status: queued|processing|success|failed
    files JSONB DEFAULT '[]'::jsonb,         -- A JSON array of all files in the batch
    total_files INTEGER DEFAULT 0,
    total_bytes BIGINT DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT now(),    -- When the batch was queued/created
    finished_at TIMESTAMPTZ,                 -- When the batch finished (success or failed)
    error TEXT,                              -- Stores error details on failure
    extra JSONB
);

CREATE INDEX IF NOT EXISTS idx_ingest_manifest_status ON ingestion_manifest(status);
CREATE INDEX IF NOT EXISTS idx_ingest_manifest_started_at ON ingestion_manifest(started_at);

-- 3. Real-time Notification Trigger
-- This function and trigger send a NOTIFY signal whenever a manifest
-- is created or its status is updated. Clients may bridge LISTEN/NOTIFY
-- to Redis or other systems.
CREATE OR REPLACE FUNCTION ingestion_manifest_notify() RETURNS trigger AS $$
DECLARE
    payload JSON;
BEGIN
    -- Construct a consistent JSON payload for the notification
    payload := json_build_object(
        'type', 'ingest.manifest',
        'action', TG_OP, -- The operation: INSERT or UPDATE
        'batch_tag', NEW.batch_tag,
        'status', NEW.status,
        'total_files', NEW.total_files,
        'total_bytes', NEW.total_bytes,
        'timestamp', now()
    );
    -- Send the notification on the 'ingest_manifest' channel
    PERFORM pg_notify('ingest_manifest', payload::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ingestion_manifest_notify ON ingestion_manifest;
CREATE TRIGGER trg_ingestion_manifest_notify
AFTER INSERT OR UPDATE ON ingestion_manifest
FOR EACH ROW EXECUTE FUNCTION ingestion_manifest_notify();

/*
The New Ingestion Workflow
This manifest changes the ingestion flow to be more controlled and auditable.

1) Producer Creates Manifest
    - Before dropping files, a Producer creates a row with status='queued' and
      populates files with the names of all .msgpack files. A unique batch_tag identifies the run.

2) Producer Drops Files
    - Files are placed into the spool/incoming directory.

3) Consumer Claims Batch
    - A Consumer (e.g., Go service or spool_watcher) is notified of the manifest and
      first UPDATEs status to 'processing' as a lock to avoid duplicate processing.

4) Consumer Processes Files
    - The Consumer processes the files listed in the manifest's files array.

5) Consumer Updates Manifest
    - On success: UPDATE status='success', set finished_at.
    - On failure: UPDATE status='failed', set finished_at and error details.

Key Benefits
- Traceability: Queryable record of each batch across its lifecycle.
- Error Handling: Failed batches are clearly marked and can be reprocessed.
- Observability: Power dashboards to show real-time pipeline status and throughput.
- Idempotency: Status gating prevents duplicate processing of the same batch.
*/
