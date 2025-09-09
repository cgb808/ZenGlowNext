# Edge Function Redis Client Wrapper

Use a Redis client library (wrapper) inside Supabase Edge Functions to perform low-latency cache reads/writes and pub/sub.

## Example (TypeScript / Deno)

```ts
// supabase/functions/my-redis-function/index.ts
import { createClient } from 'npm:redis';
import { corsHeaders } from '../_shared/cors.ts';

// Initialize once per isolate (reuse between requests)
const redisClient = createClient({ url: Deno.env.get('REDIS_URL')! });
await redisClient.connect();

Deno.serve(async (req) => {
  try {
    const key = 'user:123:profile';
    let cached = await redisClient.get(key);
    if (cached) {
      return new Response(cached, { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }
    const value = { name: 'Jane Doe', plan: 'premium' };
    await redisClient.set(key, JSON.stringify(value), { EX: 600 });
    return new Response(JSON.stringify(value), { headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
  } catch (err) {
    return new Response(JSON.stringify({ error: (err as Error).message }), { status: 500 });
  }
});
```

Notes:
- Create the client outside the handler to reuse connections.
- Prefer short TTLs for volatile data; use messagepack when sizes matter (our Python app already uses msgpack-first).
- For pub/sub, use a dedicated subscriber connection (`redisClient.duplicate()`).
