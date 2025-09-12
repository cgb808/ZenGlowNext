-- Partition & BRIN maintenance reference for doc_embeddings
-- Execute manually or adapt into migrations.

-- Example: convert existing table (manual steps summarised, not auto-run):
-- 1. CREATE TABLE doc_embeddings_new ( ... , created_at timestamptz NOT NULL) PARTITION BY RANGE (created_at);
-- 2. CREATE partitions for historical ranges.
-- 3. INSERT INTO doc_embeddings_new SELECT * FROM doc_embeddings;
-- 4. ALTER TABLE doc_embeddings RENAME TO doc_embeddings_old;
-- 5. ALTER TABLE doc_embeddings_new RENAME TO doc_embeddings;
-- 6. Drop old table after validation.

-- Create future monthly partitions (if parent already partitioned by RANGE):
-- DO $$
-- DECLARE
--   start_month date := date_trunc('month', now())::date;
--   i int;
-- BEGIN
--   FOR i IN 0..2 LOOP  -- next 3 months
--     PERFORM 1;
--     EXECUTE format('
--       CREATE TABLE IF NOT EXISTS doc_embeddings_y%sm%s PARTITION OF doc_embeddings
--       FOR VALUES FROM (%L) TO (%L)',
--       to_char(start_month + (i||' month')::interval, 'YYYY'),
--       to_char(start_month + (i||' month')::interval, 'MM'),
--       (start_month + (i||' month')::interval)::timestamptz,
--       (date_trunc('month', start_month + ((i+1)||' month')::interval))::timestamptz
--     );
--   END LOOP;
-- END $$;

-- BRIN index on created_at (lightweight for pruning):
CREATE INDEX IF NOT EXISTS doc_embeddings_created_at_brin ON doc_embeddings USING BRIN (created_at);
