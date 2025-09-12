// supabase/functions/embedding-processor/index.ts
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

console.log("Embedding processor started.");

const EMBED_ENDPOINT = Deno.env.get("EMBED_ENDPOINT") || "http://127.0.0.1:8000/model/embed";

Deno.serve(async (req) => {
  if (req.method !== 'POST') {
    return new Response("Method Not Allowed", { status: 405, headers: corsHeaders });
  }

  try {
    const { time, id } = await req.json();

    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    // 1. Call a Postgres function to select and lock the specific row.
    // This is the key to safe concurrency. If the row is already locked by another
    // parallel run of this function, it will return nothing, and we can exit safely.
    const { data: event, error: rpcError } = await supabaseClient
      .rpc('get_and_lock_unembedded_event', { event_time: time, event_id: id });

    if (rpcError) throw rpcError;

    // If no event is returned, it means another worker processed it.
    if (!event) {
      return new Response(JSON.stringify({ message: "Event already processed or locked." }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 2. Call the external embedding service.
    const embedResponse = await fetch(EMBED_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texts: [event.content] }),
    });

    if (!embedResponse.ok) {
      throw new Error(`Embedding service failed with status ${embedResponse.status}`);
    }
    const { embeddings } = await embedResponse.json();
    const embedding = embeddings[0];

    // 3. Update the row with the new embedding.
    const { error: updateError } = await supabaseClient
      .from('conversation_events')
      .update({
        embedding: embedding,
        embedded: true,
        content_hash: event.content_hash || new TextEncoder().encode(event.content).digest('hex')
      })
      .eq('time', time)
      .eq('id', id);

    if (updateError) throw updateError;

    return new Response(JSON.stringify({ success: true, eventId: id }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Processor error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    });
  }
});
