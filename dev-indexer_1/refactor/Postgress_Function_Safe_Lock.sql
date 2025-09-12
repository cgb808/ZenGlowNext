-- Function to safely fetch and lock a single unembedded event.
-- Returns the row if successful, or NULL if the row is already locked.
CREATE OR REPLACE FUNCTION get_and_lock_unembedded_event(event_time timestamptz, event_id uuid)
RETURNS TABLE (
    content text,
    content_hash text
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ce.content,
        ce.content_hash
    FROM
        conversation_events ce
    WHERE
        ce.time = event_time AND ce.id = event_id
        AND ce.embedded = FALSE
        AND ce.embedding IS NULL
    FOR UPDATE SKIP LOCKED;
END;
$$ LANGUAGE plpgsql;
