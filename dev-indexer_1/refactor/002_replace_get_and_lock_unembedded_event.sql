-- Replace RPC function with the provided PL/pgSQL version returning content and content_hash only
create or replace function public.get_and_lock_unembedded_event(event_time timestamptz, event_id uuid)
returns table (
    content text,
    content_hash text
) as $$
begin
    return query
    select ce.content, ce.content_hash
    from public.conversation_events ce
    where ce.time = event_time
      and ce.id = event_id
      and coalesce(ce.embedded, false) = false
      and ce.embedding is null
    for update skip locked;
end;
$$ language plpgsql security definer;

grant execute on function public.get_and_lock_unembedded_event(timestamptz, uuid) to anon, authenticated, service_role;
