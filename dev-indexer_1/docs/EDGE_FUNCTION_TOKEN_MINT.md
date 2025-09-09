# Edge Function: Token Mint after Voice Login (Sample)

This example shows a minimal HTTP function that, after verifying a voice login claim, mints a pseudonymous token in the PII vault and returns it to the client.

Notes:
- Keep PII in the PII DB only. This function connects to the PII DB.
- Use connection pooling provided by the edge runtime.

Pseudo-code (TypeScript-like):

```ts
import { serve } from "std/http/server.ts";
import { Pool } from "pg"; // e.g., deno-postgres or platform pool

const pool = new Pool(Deno.env.get("PII_DATABASE_URL")!, 3, true);

async function mintToken(identityId: string, purpose: string, ttlDays: number): Promise<string> {
  const client = await pool.connect();
  try {
    const res = await client.queryObject<{ token: string }>`
      SELECT mint_user_token(${identityId}, ${purpose}, ${ttlDays}) AS token;
    `;
    return res.rows[0]?.token ?? "";
  } finally {
    client.release();
  }
}

serve(async (req) => {
  try {
    const { identity_id, voice_assertion } = await req.json();
    // TODO: validate voice_assertion (signed claim)
    if (!identity_id) return new Response("missing identity_id", { status: 400 });
    const token = await mintToken(identity_id, "voice_auth", 30);
    if (!token) return new Response("token mint failed", { status: 500 });
    return new Response(JSON.stringify({ token }), { headers: { "content-type": "application/json" } });
  } catch (e) {
    return new Response(`error: ${e}`, { status: 500 });
  }
});
```

Wire this behind appropriate authentication and rate limits. Never return PII.
