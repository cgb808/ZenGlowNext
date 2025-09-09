# Redis Pub/Sub Edge Function (Supabase Edge / Deno)

A minimal Edge Function to publish/subscribe Redis messages from Supabase Edge Functions.

- Entry: `index.ts`
- Client: `npm:redis@4.7.0` (supported in Supabase Edge runtime)

## 1) Make Redis reachable

- Managed Redis (Upstash/Redis Cloud/ElastiCache): use the provider URL/host:port. Prefer TLS with `rediss://`.
- Self-hosted in VPC: place Redis in a private VPC and enable Supabase Private Link so Edge Functions can route to it.
- Or expose Redis via public IP with firewall rules restricted to Supabase Edge CIDR ranges (see Supabase docs for current CIDRs).

## 2) Store the connection string as a secret

Set the secret in your Supabase project. Edge Functions will read `Deno.env.get("REDIS_URL")`.

```bash
supabase secrets set REDIS_URL=rediss://username:password@my-redis-host:6379
```

## 3) Deploy the function

```bash
supabase functions deploy redis-pubsub --project-ref <PROJECT_REF>
```

After deployment, the URL is:

```
https://<PROJECT_REF>.functions.supabase.co/redis-pubsub
```

## 4) Call it

- Publish

```bash
curl -X POST https://<PROJECT_REF>.functions.supabase.co/redis-pubsub \
  -H "Content-Type: application/json" \
  -d '{"action":"publish","channel":"orders","message":"order_created:123"}'
```

- Subscribe (waits for first message or times out; default 15s, configurable via `timeoutMs`)

```bash
curl -X POST https://<PROJECT_REF>.functions.supabase.co/redis-pubsub \
  -H "Content-Type: application/json" \
  -d '{"action":"subscribe","channel":"orders"}'
```

- Optional long-running background listener (returns 202 immediately):
  Send `{ "action": "listen", "channel": "orders" }` and move processing into the background using the Edge Runtime's `waitUntil` hook (see `index.ts`).

## 5) Notes

- Actions: `publish`, `subscribe`, `listen`.
- Errors return JSON with appropriate HTTP status codes (400/504).

## 6) Security checklist

- Use TLS: prefer `rediss://` (or a VPN if using `redis://`).
- Restrict ingress: allow-list Supabase Edge CIDR blocks if exposing a public IP.
- Least-privilege: scope the Redis user to only the commands you need.
- Rate limit: consider basic throttling in the function or Supabase API limits.
