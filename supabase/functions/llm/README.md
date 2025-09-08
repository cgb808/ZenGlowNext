# llm Edge Function

Renamed from `llm-proxy`.

POST `/functions/v1/llm`

Request JSON:
```
{ "prompt": "Explain vector search", "model": "gemma:2b", "stream": false }
```

Response JSON (non-stream):
```
{ "response": "...", "model": "gemma:2b", "latency_ms": 312 }
```

Streaming (if `stream: true`) returns raw text chunks.

Environment:
- MODEL_URL
- MODEL_NAME
- ALLOW_ORIGIN
- GEN_TIMEOUT_MS (default 60000)
- ALLOW_MODELS (comma or space separated allowlist)

Deploy:
```
supabase functions deploy llm --project-ref <ref>
```

Local dev:
```
supabase functions serve llm --env-file ./supabase/.env.local
```
