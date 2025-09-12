// PII Gate management: ensure/open/close/status per scope
// Env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

import { createClient } from "npm:@supabase/supabase-js@2.45.4";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

type Body = { action: "ensure" | "open" | "close" | "status"; scope?: string };

const supabaseUrl = Deno.env.get("SUPABASE_URL");
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
if (!supabaseUrl || !supabaseKey) console.warn("pii-gate missing SUPABASE envs");
const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey, { auth: { persistSession: false } }) : null;

console.info("pii-gate Edge Function booted");

Deno.serve(async (req: Request) => {
  if (!supabase) return jsonResponse({ error: "server not configured" }, 500);
  if (req.method !== "POST") return jsonResponse({ error: "Only POST supported" }, 405);
  let body: Body;
  try { body = await req.json(); } catch { return jsonResponse({ error: "Invalid JSON" }, 400); }
  const scope = body.scope || "global";
  const now = new Date().toISOString();

  if (body.action === "ensure") {
    const { error } = await supabase.from("pii_gate_lock").upsert({ scope, is_open: false, updated_at: now }, { onConflict: "scope" });
    if (error) return jsonResponse({ error: error.message }, 500);
    return jsonResponse({ scope, is_open: false });
  }
  if (body.action === "open") {
    const { error } = await supabase.from("pii_gate_lock").upsert({ scope, is_open: true, updated_at: now }, { onConflict: "scope" });
    if (error) return jsonResponse({ error: error.message }, 500);
    return jsonResponse({ scope, is_open: true });
  }
  if (body.action === "close") {
    const { error } = await supabase.from("pii_gate_lock").upsert({ scope, is_open: false, updated_at: now }, { onConflict: "scope" });
    if (error) return jsonResponse({ error: error.message }, 500);
    return jsonResponse({ scope, is_open: false });
  }
  if (body.action === "status") {
    const { data, error } = await supabase.from("pii_gate_lock").select("scope,is_open,updated_at").eq("scope", scope).maybeSingle();
    if (error) return jsonResponse({ error: error.message }, 500);
    return jsonResponse(data ?? { scope, is_open: false });
  }
  return jsonResponse({ error: "Unsupported action" }, 400);
});
