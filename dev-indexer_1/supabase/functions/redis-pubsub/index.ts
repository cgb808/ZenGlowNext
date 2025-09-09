// Minimal Redis Pub/Sub Edge Function for Supabase Edge (Deno)
// Uses the official node-redis v4 client via npm: specifier (supported in Edge runtime)
// Exposes two actions: publish and subscribe (single message with timeout)

import { createClient, type RedisClientType } from "npm:redis@4.7.0";

let redis: RedisClientType | null = null;

async function getRedisClient(): Promise<RedisClientType> {
  if (redis && redis.isOpen) return redis;
  const url = Deno.env.get("REDIS_URL");
  if (!url) throw new Error("REDIS_URL secret not set");

  const client = createClient({ url });
  client.on("error", (err) => console.error("Redis error:", err));
  await client.connect();
  redis = client;
  return client;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

console.info("redis-pubsub Edge Function booted");

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") {
    return jsonResponse({ error: "Only POST is supported" }, 405);
  }

  let payload: { action?: string; channel?: string; message?: string; timeoutMs?: number };
  try {
    payload = await req.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const { action, channel, message } = payload;
  const timeoutMs = Math.max(1000, Math.min(payload?.timeoutMs ?? 15000, 60000));

  if (!action || !channel) {
    return jsonResponse({ error: "Missing required fields: action, channel" }, 400);
  }

  const client = await getRedisClient();

  if (action === "publish") {
    if (!message) return jsonResponse({ error: "Publish requires a message" }, 400);
    await client.publish(channel, message);
    return jsonResponse({ status: "published", channel });
  }

  if (action === "subscribe") {
    const subscriber = client.duplicate();
    await subscriber.connect();

    const firstMsg = new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => {
        subscriber.unsubscribe(channel).catch(() => {});
        reject(new Error("Timeout waiting for message"));
      }, timeoutMs);

      subscriber.subscribe(channel, (msg) => {
        clearTimeout(timer);
        subscriber.unsubscribe(channel).catch(() => {});
        resolve(msg);
      });
    });

    try {
      const received = await firstMsg;
      return jsonResponse({ channel, message: received });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "unknown";
      return jsonResponse({ error: msg }, 504);
    } finally {
      subscriber.disconnect().catch(() => {});
    }
  }

  if (action === "listen") {
    // Long-running background subscriber example: do not hold the HTTP response open
    const sub = client.duplicate();
    await sub.connect();
    const channelName = channel;

    // run in background
    // deno-lint-ignore no-explicit-any
    (globalThis as any).EdgeRuntime?.waitUntil?.(
      (async () => {
        await sub.subscribe(channelName, async (msg) => {
          console.log(`Received ${msg} on ${channelName}`);
          // TODO: add processing logic here (DB insert, webhook call, etc.)
        });
      })()
    );

    return jsonResponse({ status: "listener started", channel: channelName }, 202);
  }

  return jsonResponse({ error: `Unsupported action '${action}'` }, 400);
});
