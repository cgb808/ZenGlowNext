// Supabase Edge Function: llm-proxy
// Purpose: Proxy application prompts to a remote/local Ollama model host.
// Method: POST { prompt: string, model?: string, stream?: boolean }
// Response: { response: string, model: string, latency_ms: number }
// Optional streaming (if stream=true) will passthrough SSE tokens.

// Environment Variables (configure via `supabase secrets set`):
//   MODEL_URL   - Base URL to Ollama host (e.g. http://203.0.113.10:11434)
//   MODEL_NAME  - Default model (e.g. gemma:2b)
//   ALLOW_ORIGIN - CORS origin (optional, default '*')

// deno-lint-ignore-file
// @ts-nocheck
// NOTE: Type checks are disabled because Supabase Edge runtime supplies Deno APIs
// and remote module resolution that may not be available in local TS tooling.
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const MODEL_URL = Deno.env.get("MODEL_URL") ?? ""; // Intentionally blank if unset
const DEFAULT_MODEL = Deno.env.get("MODEL_NAME") ?? "gemma:2b";
const ALLOW_ORIGIN = Deno.env.get("ALLOW_ORIGIN") ?? "*";
const GEN_TIMEOUT_MS = parseInt(Deno.env.get("GEN_TIMEOUT_MS") ?? "60000", 10);
// Comma/space separated allow list; if set, restrict requested models
const RAW_ALLOW_MODELS = Deno.env.get("ALLOW_MODELS") ?? "";
const ALLOW_MODELS = RAW_ALLOW_MODELS.split(/[ ,]+/).map(s => s.trim()).filter(Boolean);

const corsHeaders: Record<string,string> = {
  "Access-Control-Allow-Origin": ALLOW_ORIGIN,
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST,OPTIONS",
};

console.log(`[llm-proxy] Edge Function start MODEL_URL=${MODEL_URL || '(unset)'} DEFAULT_MODEL=${DEFAULT_MODEL} timeout=${GEN_TIMEOUT_MS}ms allow_models=${ALLOW_MODELS.join(',') || '*'} `);

type GeneratePayload = {
  prompt: string;
  model?: string;
  stream?: boolean;
  system?: string;
  max_new_tokens?: number;
};

serve(async (req: Request): Promise<Response> => {
  if (req.method === "OPTIONS") {
    return new Response("", { headers: corsHeaders });
  }
  if (req.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405, headers: corsHeaders });
  }
  let body: GeneratePayload;
  try {
    body = await req.json();
  } catch(_) {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" }});
  }
  if (!body?.prompt || typeof body.prompt !== 'string') {
    return new Response(JSON.stringify({ error: "Missing prompt" }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" }});
  }
  if (!MODEL_URL) {
    return new Response(JSON.stringify({ error: "MODEL_URL_not_configured" }), { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" }});
  }
  const targetModel = body.model || DEFAULT_MODEL;
  if (ALLOW_MODELS.length && !ALLOW_MODELS.includes(targetModel)) {
    return new Response(JSON.stringify({ error: "model_not_allowed", model: targetModel }), { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" }});
  }
  const stream = !!body.stream;
  const genPayload = {
    model: targetModel,
    prompt: body.prompt,
    stream,
    // Pass through system prompt if provided
    system: body.system,
    options: body.max_new_tokens ? { num_predict: body.max_new_tokens } : undefined,
  };
  const url = MODEL_URL.replace(/\/$/, '') + '/api/generate';
  const started = performance.now();
  const ac = new AbortController();
  const to = setTimeout(() => ac.abort(), GEN_TIMEOUT_MS);
  try {
    const upstream = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(genPayload),
      signal: ac.signal,
    });
    clearTimeout(to);
    if (!stream) {
      if (!upstream.ok) {
        return new Response(JSON.stringify({ error: `Upstream ${upstream.status}` }), { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" }});
      }
      const j = await upstream.json();
      const latency = Math.round(performance.now() - started);
      return new Response(JSON.stringify({ response: j.response, model: targetModel, latency_ms: latency }), { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" }});
    }
    // Streaming mode: verify upstream OK first
    if (!upstream.ok) {
      return new Response(JSON.stringify({ error: `Upstream ${upstream.status}` }), { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" }});
    }
    // Streaming (proxy SSE / chunked lines)
    const { readable, writable } = new TransformStream();
    (async () => {
      const writer = writable.getWriter();
      try {
        const reader = upstream.body?.getReader();
        if (!reader) throw new Error('No upstream body');
        const decoder = new TextDecoder();
        const encoder = new TextEncoder();
        let acc = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
            acc += decoder.decode(value, { stream: true });
            // Ollama streaming returns JSON objects per line
            const lines = acc.split(/\n+/);
            acc = lines.pop() || '';
            for (const line of lines) {
              if (!line.trim()) continue;
              try {
                const obj = JSON.parse(line);
                if (obj.response) {
                  await writer.write(encoder.encode(obj.response));
                }
              } catch { /* ignore partial */ }
            }
        }
      } catch (e) {
        console.error('[llm-proxy stream] error', e);
        try { await writable.abort(e); } catch {}
      } finally {
        await writer.close();
      }
    })();
    return new Response(readable, { status: upstream.status, headers: { ...corsHeaders, 'Content-Type': 'text/plain' }});
  } catch (e) {
    console.error('[llm-proxy] upstream error', e);
    if ((e as any).name === 'AbortError') {
      return new Response(JSON.stringify({ error: 'upstream_timeout', timeout_ms: GEN_TIMEOUT_MS }), { status: 504, headers: { ...corsHeaders, "Content-Type": "application/json" }});
    }
    return new Response(JSON.stringify({ error: 'Upstream fetch failed' }), { status: 502, headers: { ...corsHeaders, "Content-Type": "application/json" }});
  }
});
