-- Create RPC function for safe concurrency when embedding events
-- Expects table conversation_events(time timestamptz, id uuid, content text, embedded boolean, content_hash text, embedding vector? etc.)
-- Adjust types/columns as needed to match your schema.

create or replace function public.get_and_lock_unembedded_event(event_time timestamptz, event_id uuid)
returns table (
  time timestamptz,
  id uuid,
  content text,
  content_hash text,
  embedded boolean
) language sql security definer as $$
  -- Use SKIP LOCKED to avoid waiting on locked rows
  select ce.time, ce.id, ce.content, ce.content_hash, ce.embedded
  from public.conversation_events ce
  where ce.time = event_time
    and ce.id = event_id
    and (ce.embedded is false or ce.embedded is null)
  for update skip locked;
$$;

-- Grant execute to anon and service roles as appropriate
grant execute on function public.get_and_lock_unembedded_event(timestamptz, uuid) to anon, authenticated, service_role;
