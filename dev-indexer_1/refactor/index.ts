// @ts-nocheck
// supabase/functions/embedding-orchestrator/index.ts
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

console.log('Embedding orchestrator started.')

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  // Prefer POST; block others for manual invocation security
  if (req.method !== 'POST') {
    return new Response('Method Not Allowed', { status: 405, headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // 1. Fetch up to N unembedded events (id/time only)
    const { data: events, error: selectError } = await supabaseClient
      .from('conversation_events')
      .select('time, id')
      .is('embedding', null)
      .eq('embedded', false)
      .limit(100)

    if (selectError) throw selectError

    if (!events || events.length === 0) {
      return new Response(JSON.stringify({ message: 'No new events to process.' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      })
    }

    // 2. Fan out to the processor for each event (fire and forget, but observe failures)
    const invocations = events.map((event) =>
      supabaseClient.functions.invoke('embedding-processor', {
        body: { time: event.time, id: event.id },
      })
    )

    const results = await Promise.allSettled(invocations)
    const failedInvocations = results.filter((r) => r.status === 'rejected').length

    return new Response(
      JSON.stringify({
        message: `Triggered embedding for ${events.length} events`,
        failedInvocations,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )
  } catch (error) {
    console.error('Orchestrator error:', error)
    return new Response(JSON.stringify({ error: (error as Error).message }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      status: 500,
    })
  }
})
