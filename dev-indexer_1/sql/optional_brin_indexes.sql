-- Optional BRIN Indexes (lightweight range pruning)
-- Safe to re-run; uses IF NOT EXISTS / exceptions handled.
-- Applied automatically by db_apply.sh after core schema.

-- conversation_events time-based pruning
CREATE INDEX IF NOT EXISTS brin_conversation_events_time
  ON conversation_events USING brin (time);

-- pii_access_log time-based pruning (if table present and in same DB)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='pii_access_log') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS brin_pii_access_log_ts ON pii_access_log USING brin (ts)';
    END IF;
END$$;

-- token validity window (valid_from, valid_until) if PII token map exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='pii_token_map') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS brin_pii_token_valid ON pii_token_map USING brin (valid_from, valid_until)';
    END IF;
END$$;
