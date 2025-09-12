// supabase/functions/embedding-orchestrator/index.ts
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

console.log("Embedding orchestrator started.");

Deno.serve(async (req) => {
  // This function should be triggered by a Supabase Cron Job, but we
  // add a manual invocation check for security.
  if (req.method !== 'POST') {
    return new Response("Method Not Allowed", { status: 405, headers: corsHeaders });
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    );

    // 1. Find a batch of unembedded events. We only need the primary keys.
    const { data: events, error: selectError } = await supabaseClient
      .from('conversation_events')
      .select('time, id')
      .is('embedding', null)
      .eq('embedded', false)
      .limit(100); // Process up to 100 events per run

    if (selectError) throw selectError;
    if (!events || events.length === 0) {
      return new Response(JSON.stringify({ message: "No new events to process." }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      });
    }

    // 2. "Fan out" the work by invoking the processor function for each event.
    // We don't wait for these to complete ("fire and forget").
    const invocationPromises = events.map(event =>
      supabaseClient.functions.invoke('embedding-processor', {
        body: { time: event.time, id: event.id },
      })
    );

    // Although we don't need the results, it's good practice to log if invocations failed.
    const results = await Promise.allSettled(invocationPromises);
    const failedInvocations = results.filter(r => r.status === 'rejected').length;

    return new Response(JSON.stringify({
      message: `Successfully triggered embedding for ${events.length} events.`,
      failedInvocations: failedInvocations,
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 200,
    });

  } catch (error) {
    console.error('Orchestrator error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    });
  }
});
