// Events recent: recall recent events from Postgres for dashboards/agents
// Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

import { createClient } from "npm:@supabase/supabase-js@2.45.4";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const supabaseUrl = Deno.env.get("SUPABASE_URL");
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
if (!supabaseUrl || !supabaseKey) console.warn("events-recent missing SUPABASE envs");
const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey, { auth: { persistSession: false } }) : null;

console.info("events-recent Edge Function booted");

Deno.serve(async (req: Request) => {
  if (!supabase) return jsonResponse({ error: "server not configured" }, 500);
  const url = new URL(req.url);
  const channel = url.searchParams.get("channel") ?? undefined;
  const batchTag = url.searchParams.get("batch_tag") ?? undefined;
  const since = url.searchParams.get("since") ?? undefined; // ISO8601
  const limit = Math.max(1, Math.min(Number(url.searchParams.get("limit") ?? "50"), 500));

  let q = supabase.from("ingest_events").select("*", { count: "estimated" }).order("ts", { ascending: false }).limit(limit);
  if (channel) q = q.eq("channel", channel);
  if (batchTag) q = q.eq("batch_tag", batchTag);
  if (since) q = q.gte("ts", since);

  const { data, error, count } = await q;
  if (error) return jsonResponse({ error: error.message }, 500);
  return jsonResponse({ count, data });
});
