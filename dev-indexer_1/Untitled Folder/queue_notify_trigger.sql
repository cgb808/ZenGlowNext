-- queue_notify_trigger.sql
-- Adds a trigger to send a NOTIFY on new pending rows so LISTEN-capable workers
-- can wake immediately instead of polling.
-- Safe to apply multiple times (idempotent creation of function / trigger).

CREATE OR REPLACE FUNCTION public.notify_code_chunk_ingest() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  payload JSON;
BEGIN
  -- Only notify on freshly inserted pending rows
  IF (TG_OP = 'INSERT') THEN
    IF NEW.status = 'pending' THEN
      payload = json_build_object('id', NEW.id, 'checksum', NEW.checksum, 'file_path', NEW.file_path);
      PERFORM pg_notify('code_chunk_ingest', payload::text);
    END IF;
  END IF;
  RETURN NEW;
END;$$;

DROP TRIGGER IF EXISTS code_chunk_ingest_notify ON public.code_chunk_ingest_queue;
CREATE TRIGGER code_chunk_ingest_notify
AFTER INSERT ON public.code_chunk_ingest_queue
FOR EACH ROW EXECUTE FUNCTION public.notify_code_chunk_ingest();
