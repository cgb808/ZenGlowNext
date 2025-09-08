# llm-proxy Edge Function

Proxies application prompts to a remote Ollama model host.

## Endpoint
POST `/functions/v1/llm-proxy`

### Request JSON
```
{ "prompt": "Explain vector search", "model": "gemma:2b", "stream": false }
```

### Response JSON (non-stream)
```
{ "response": "...", "model": "gemma:2b", "latency_ms": 312 }
```

If `stream: true` the response body is plain text chunks of the model output (one or more tokens/segments per chunk).

## Environment Variables
| Name | Purpose | Example |
|------|---------|---------|
| MODEL_URL | Base URL of Ollama host | http://203.0.113.10:11434 |
| MODEL_NAME | Default model name | gemma:2b |
| ALLOW_ORIGIN | CORS allow origin | https://app.example.com |

Set secrets:
```
supabase secrets set MODEL_URL=https://model.example.net:11434 MODEL_NAME="gemma:2b" ALLOW_ORIGIN=https://yourapp.com
```

## Deploy
```
supabase functions deploy llm-proxy --project-ref <ref>
```

## Local Dev (Supabase CLI)
```
supabase functions serve llm-proxy --env-file ./supabase/.env.local
```

`supabase/.env.local`:
```
MODEL_URL=http://127.0.0.1:11434
MODEL_NAME=gemma:2b
ALLOW_ORIGIN=*
```

## Notes
* If your Ollama host is on a private LAN (e.g. 192.168.x.x) the cloud Edge Function cannot reach it. Expose it securely (VPN, reverse proxy, tunnel) or self-host Supabase within the same network.
* Streaming mode strips JSON framing and forwards raw token text.
* For multi-tenant usage, add auth & rate limiting before hitting the upstream model.
