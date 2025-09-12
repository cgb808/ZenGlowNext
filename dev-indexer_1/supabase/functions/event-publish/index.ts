// Event publish Edge Function: validates, (optionally) persists to Postgres, then publishes to Redis
// Env: REDIS_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ALLOWED_CHANNELS (comma), MAX_MESSAGE_BYTES (int), PERSIST_DEFAULT ("true"/"false"), TIMESCALE_TABLE (optional)

import { createClient as createRedis, type RedisClientType } from "npm:redis@4.7.0";
import { createClient as createSupabase } from "npm:@supabase/supabase-js@2.45.4";

let redis: RedisClientType | null = null;
async function getRedis(): Promise<RedisClientType> {
  if (redis && redis.isOpen) return redis;
  const url = Deno.env.get("REDIS_URL");
  if (!url) throw new Error("REDIS_URL not set");
  const c = createRedis({ url });
  c.on("error", (e) => console.error("redis error:", e));
  await c.connect();
  redis = c;
  return c;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

type PublishBody = {
  action?: string; // expect "publish"
  channel: string;
  message: string; // JSON string payload
  persist?: boolean; // override default
};

const allowed = new Set((Deno.env.get("ALLOWED_CHANNELS") ?? "ingest_updates,embed_updates").split(",").map((s) => s.trim()).filter(Boolean));
const maxBytes = Math.max(1024, Math.min(Number(Deno.env.get("MAX_MESSAGE_BYTES") ?? 32768), 512000));
const persistDefault = (Deno.env.get("PERSIST_DEFAULT") ?? "true").toLowerCase() === "true";

const supabaseUrl = Deno.env.get("SUPABASE_URL");
const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
const supabase = supabaseUrl && supabaseKey ? createSupabase(supabaseUrl, supabaseKey, { auth: { persistSession: false } }) : null;
const timescaleTable = Deno.env.get("TIMESCALE_TABLE");
const tsWebhook = Deno.env.get("TIMESERIES_WEBHOOK_URL");

console.info("event-publish Edge Function booted");

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return jsonResponse({ error: "Only POST supported" }, 405);
  let body: PublishBody;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const { action, channel, message } = body;
  if (!channel || !message) return jsonResponse({ error: "Missing channel or message" }, 400);
  if (action && action !== "publish") return jsonResponse({ error: "Unsupported action" }, 400);
  if (!allowed.has(channel)) return jsonResponse({ error: `Channel '${channel}' not allowed` }, 403);
  const byteLen = new TextEncoder().encode(message).length;
  if (byteLen > maxBytes) return jsonResponse({ error: `message too large (${byteLen} > ${maxBytes})` }, 413);

  // Attempt to parse message to extract common fields for persistence
  let msgObj: Record<string, unknown> | null = null;
  let msgTsISO: string | null = null;
  try {
    msgObj = JSON.parse(message);
    const tsField = (msgObj as any)?.ts;
    if (typeof tsField === "number") {
      // seconds since epoch
      msgTsISO = new Date(tsField * 1000).toISOString();
    } else if (typeof tsField === "string") {
      const parsed = new Date(tsField);
      if (!isNaN(parsed.valueOf())) msgTsISO = parsed.toISOString();
    }
  } catch {
    // keep null; we still publish raw string
  }

  const doPersist = body.persist ?? persistDefault;
  if (doPersist && supabase) {
    const row: Record<string, unknown> = {
      channel,
      message: msgObj ?? { raw: message },
      ts: msgTsISO ?? new Date().toISOString(),
    };
    if (msgObj) {
      // extract common fields if present
      const keys = ["event", "batch_tag", "status", "processed", "bytes", "count", "pii"] as const;
      for (const k of keys) if (k in msgObj!) row[k] = (msgObj as any)[k];
    }
    try {
      const { error } = await supabase.from("ingest_events").insert(row);
      if (error) console.error("persist error:", error.message);
    } catch (e) {
      console.error("persist exception:", e);
    }
    if (timescaleTable) {
      // lightweight insert for time-series metrics (if table exists and extension enabled)
      try {
        const tsRow = {
          ts: new Date().toISOString(),
          channel,
          event: msgObj && typeof msgObj.event === "string" ? (msgObj.event as string) : null,
          batch_tag: msgObj && typeof msgObj.batch_tag === "string" ? (msgObj.batch_tag as string) : null,
          pii: msgObj && typeof (msgObj as any).pii === "boolean" ? (msgObj as any).pii : null,
        };
        const { error } = await supabase.from(timescaleTable).insert(tsRow as any);
        if (error) console.error("timescale insert error:", error.message);
      } catch (e) {
        console.error("timescale insert exception:", e);
      }
    }
  }

  // Publish to Redis
  try {
    const r = await getRedis();
    await r.publish(channel, message);
  } catch (e) {
    console.error("redis publish error:", e);
    return jsonResponse({ error: "publish failed" }, 502);
  }

  // Optional external timeseries mirror (before responding)
  if (tsWebhook && msgObj) {
    try {
      const minimal = {
        ts: msgTsISO ?? new Date().toISOString(),
        channel,
        event: typeof msgObj.event === "string" ? msgObj.event : null,
        batch_tag: typeof msgObj.batch_tag === "string" ? msgObj.batch_tag : null,
      };
      await fetch(tsWebhook, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(minimal) });
    } catch (e) {
      console.error("timeseries webhook error:", e);
    }
  }

  return jsonResponse({ status: "published", channel, persisted: !!(doPersist && supabase) });
});
