// deno-lint-ignore-file
// @ts-nocheck
// Supabase Edge Function: curate-code (enhanced for repo fetch + batch ingestion)
// Purpose: Lightweight ingestion of code chunks into a staging queue for asynchronous
// embedding + enrichment. Avoids large ONNX model loads inside Edge runtime.
// -----------------------------------------------------------------------------
// FUTURE IMPLEMENTATION NOTES (non-functional annotations):
// 1. Rate Limiting: Introduce per X-Zendexer-Key + IP sliding window (e.g. Redis or
//    Postgres advisory locking) before processing to mitigate abuse.
// 2. Structured Audit Logging: Create table code_chunk_ingest_log capturing
//    (ingest_id, file_path, checksum, repository, status, latency_ms, bytes) and
//    insert a log row after enqueue attempt.
// 3. Worker Signal Channel: Add optional NOTIFY payload after successful insert to
//    wake an ingestion worker (or use pgmq / supabase realtime channel).
// 4. Repo Content Caching: Cache fetched GitHub file blobs keyed by (repo, path, ref,
//    sha) to reduce duplicate API calls when batching large repositories.
// 5. Enhanced Security: Support JWT bearer auth & role claims in addition to shared
//    secret; map roles to allowed repositories via a policy table.
// 6. Commit / Ref Traceability: Extend queue schema with commit_sha + ref fields if
//    provided, enabling historical reconstruction and delta indexing.
// 7. Multi-Chunk Splitting: Allow a 'source_content' field and perform deterministic
//    code splitting server-side (size heuristics) to reduce client complexity.
// 8. Content Hash Normalization: Optionally normalize line endings + trim trailing
//    whitespace prior to checksum to stabilize dedupe across platforms.
// 9. Metrics Endpoint: Expose lightweight GET /?stats=1 returning counts by status,
//    average latency, oldest pending age for monitoring.
// 10. Quarantine Mode: If repository not on allowlist, optionally queue as
//     status='quarantine' for manual review instead of hard reject.
// 11. Pre-Filter: Add optional regex allow/deny lists for file_path (e.g. skip large
//     vendor or binary files) before accepting.
// 12. Encryption (Optional): If sensitive code, integrate envelope encryption using a
//     KMS-managed key before storing raw content, decrypt only in worker.
// 13. Retry Semantics: For transient fetch_github failures, implement limited retry
//     with exponential backoff (respecting Edge runtime constraints).
// 14. Batch Partial Failures: Provide client option 'abort_on_error=false' to proceed
//     with other chunks even if one fails early; currently this is implicit but error
//     granularity messaging can be improved with standardized code map.
// 15. (IN PROGRESS) Basic in-memory rate limiting stub implemented (per key+IP) – NOT
//     durable across edge instance restarts; upgrade to Redis/DB for production.
// -----------------------------------------------------------------------------
//
// NEW (repo fetch + batch ingestion):
//  - If content omitted but repository (owner/repo) + file_path provided, attempts to fetch
//    file content from GitHub using GITHUB_PAT (if set) or unauthenticated fallback.
//  - Supports batch mode: POST { chunks: [ { file_path, repository, ref?, ... } ], context? }
//  - Repo allowlist via ALLOWED_REPOS (comma/space list). If set, only listed repos allowed.
//  - Size guards: MAX_CONTENT_BYTES per file, MAX_BATCH_ITEMS (default 25) total.
//
// Method (single): POST { chunk: { file_path, content? or (repository+ref?) , language?, repository?, start_line?, end_line?, metadata? }, context?: {...} }
// Method (batch):  POST { chunks: [ { file_path, content? or repo fetch fields ... } ], context?: {...} }
// Response single: { queued: true, checksum, deduplicated?: boolean, confidence? }
// Response batch:  { results: [ { file_path, repository, queued, checksum, error? } ] }
//
// Optional: GET /?checksum=...  -> status lookup in queue
// Optional batch status: GET /?checksums=hex1,hex2,...
//
// Environment Variables (set via `supabase secrets set`):
//   SUPABASE_URL
//   SUPABASE_SERVICE_ROLE_KEY  (consider a dedicated limited key instead)
//   ALLOWED_ORIGIN (optional CORS; default '*')
//   MAX_CONTENT_BYTES (optional size guard; default 200_000)
//   MAX_BATCH_ITEMS (optional; default 25)
//   GITHUB_PAT (REQUIRED for any repository fetch operations; function will error if repo fetch attempted without it)
//   ALLOWED_REPOS (optional allowlist: "owner1/repo1,owner2/repo2")
//   GITHUB_API_BASE (optional override, default https://api.github.com)
//   SUPABASE_DB_URL (optional: if present + AUTO_CREATE_TABLE=1 or ?create_table=1, will attempt to create table schema directly via pg driver)
//   AUTO_CREATE_TABLE (optional: '1' to enable automatic ensure of table on each cold start)
//   QUEUE_TABLE (optional: override table name; default code_chunk_ingest_queue)
//   Usage to force create: POST/GET with ?create_table=1 (requires SUPABASE_DB_URL + appropriate role networking)
//   ZENDEXER_INGEST_KEY (required shared secret header X-Zendexer-Key for ingestion auth)
//
// Queue Processing (external worker responsibilities):
//   1. SELECT * FROM code_chunk_ingest_queue WHERE status='pending' ORDER BY created_at LIMIT N FOR UPDATE SKIP LOCKED
//   2. Generate embeddings (reusing embedding_cache by checksum)
//   3. UPSERT aggregated row into code_chunks (respect uniqueness on (file_path,start_line,end_line) or checksum)
//   4. UPDATE queue row -> status='done', store embedding dims/metadata; ON ERROR -> status='error', error_message
//   5. Optionally NOTIFY 'code_chunk_ingest' with payload JSON (checksum,id)
//
// NOTE: This function *does not* perform embedding, ensuring fast cold starts.

import { serve } from "https://deno.land/std@0.182.0/http/server.ts";
import { createClient } from "npm:@supabase/supabase-js@2.39.3";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
const ALLOWED_ORIGIN = Deno.env.get("ALLOWED_ORIGIN") ?? "*";
const MAX_CONTENT_BYTES = parseInt(Deno.env.get("MAX_CONTENT_BYTES") ?? "200000", 10);
const MAX_BATCH_ITEMS = parseInt(Deno.env.get("MAX_BATCH_ITEMS") ?? "25", 10);
const GITHUB_PAT = Deno.env.get("GITHUB_PAT") ?? Deno.env.get("GITHUB_TOKEN") ?? "";
const ALLOWED_REPOS_RAW = Deno.env.get("ALLOWED_REPOS") ?? "";
const ALLOWED_REPOS = ALLOWED_REPOS_RAW.split(/[ ,]+/).map(s => s.trim()).filter(Boolean);
const GITHUB_API_BASE = (Deno.env.get("GITHUB_API_BASE") ?? "https://api.github.com").replace(/\/$/, "");
const SUPABASE_DB_URL = Deno.env.get("SUPABASE_DB_URL") || Deno.env.get("DB_URL") || "";
const AUTO_CREATE_TABLE = Deno.env.get("AUTO_CREATE_TABLE") === "1";
const QUEUE_TABLE = Deno.env.get("QUEUE_TABLE") || "code_chunk_ingest_queue";
const ZENDEXER_INGEST_KEY = Deno.env.get("ZENDEXER_INGEST_KEY") || "";
// Rate limiting env (basic stub; in-memory only)
const RATE_LIMIT_WINDOW_MS = parseInt(Deno.env.get("RATE_LIMIT_WINDOW_MS") ?? "60000", 10); // 1 min
const RATE_LIMIT_MAX = parseInt(Deno.env.get("RATE_LIMIT_MAX") ?? "120", 10); // 120 requests / window default
const RATE_LIMIT_MAX_PERSIST = parseInt(Deno.env.get("RATE_LIMIT_MAX_PERSIST") ?? String(RATE_LIMIT_MAX), 10);
const LOG_TABLE = Deno.env.get("LOG_TABLE") || "code_chunk_ingest_log";

// In-memory rate tracking (non-durable, per-edge instance)
const rlBuckets: Map<string, number[]> = new Map();

let tableEnsured = false;
let tableEnsurePromise: Promise<void> | null = null;

async function ensureTableExists(force = false) {
  if (!SUPABASE_DB_URL) return; // nothing to do
  if (tableEnsured && !force) return;
  if (tableEnsurePromise && !force) return tableEnsurePromise;
  tableEnsurePromise = (async () => {
    try {
      const { Client } = await import("https://deno.land/x/postgres@v0.17.0/mod.ts");
      const client = new Client(SUPABASE_DB_URL);
      await client.connect();
      // Basic table
  const createSql = `CREATE TABLE IF NOT EXISTS public."${QUEUE_TABLE}" (
        id bigserial PRIMARY KEY,
        file_path text NOT NULL,
        content text NOT NULL,
        language text,
        repository text,
        start_line integer,
        end_line integer,
        metadata jsonb DEFAULT '{}'::jsonb,
        checksum text NOT NULL,
        confidence_score real,
        status text NOT NULL DEFAULT 'pending',
        error_message text,
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
      );`;
      await client.queryArray(createSql);
      const uniqueIdx = `CREATE UNIQUE INDEX IF NOT EXISTS ${QUEUE_TABLE}_file_checksum_idx ON public."${QUEUE_TABLE}" (file_path, checksum)`;
      await client.queryArray(uniqueIdx);
      const statusIdx = `CREATE INDEX IF NOT EXISTS ${QUEUE_TABLE}_status_idx ON public."${QUEUE_TABLE}" (status)`;
      await client.queryArray(statusIdx);
      const fnUpdated = `CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;`;
      await client.queryArray(fnUpdated);
      const trigger = `CREATE TRIGGER ${QUEUE_TABLE}_set_updated_at BEFORE UPDATE ON public."${QUEUE_TABLE}" FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();`;
      try { await client.queryArray(trigger); } catch { /* ignore if exists */ }
  // Ensure new columns for provenance if not present
  try { await client.queryArray(`ALTER TABLE public."${QUEUE_TABLE}" ADD COLUMN IF NOT EXISTS commit_sha text`); } catch {}
  try { await client.queryArray(`ALTER TABLE public."${QUEUE_TABLE}" ADD COLUMN IF NOT EXISTS git_ref text`); } catch {}
          // Audit log table ensure
          const logSql = `CREATE TABLE IF NOT EXISTS public."${LOG_TABLE}" (
            id bigserial PRIMARY KEY,
            ingest_key text,
            client_ip text,
            file_path text,
            repository text,
            checksum text,
            status text,
            error_code text,
            bytes integer,
            latency_ms integer,
            created_at timestamptz DEFAULT now()
          );`;
          await client.queryArray(logSql);
          try { await client.queryArray(`CREATE INDEX IF NOT EXISTS ${LOG_TABLE}_created_at_idx ON public."${LOG_TABLE}" (created_at)`); } catch {}
          try { await client.queryArray(`CREATE INDEX IF NOT EXISTS ${LOG_TABLE}_ingest_key_idx ON public."${LOG_TABLE}" (ingest_key)`); } catch {}
      tableEnsured = true;
      await client.end();
    } catch (e) {
      console.error("[curate-code] table ensure failed", e?.message || e);
    }
  })();
  return tableEnsurePromise;
}

const supabase = createClient(SUPABASE_URL, SERVICE_KEY, { auth: { persistSession: false } });

interface IncomingChunk {
  file_path: string;
  content: string;
  language?: string;
  repository?: string;
  start_line?: number;
  end_line?: number;
  metadata?: Record<string, unknown>;
  commit_sha?: string; // (new optional provenance field)
  ref?: string; // git ref (branch / tag)
}

interface ContextMeta {
  stars?: number;
  forks?: number;
  last_updated?: string; // ISO date
}

interface QueueInsertSource extends IncomingChunk {
  // ref already included above (git ref for repo fetch provenance)
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      "Access-Control-Allow-Methods": "POST,GET,OPTIONS"
    }
  });
}

function scoreConfidence(chunk: IncomingChunk, ctx?: ContextMeta): number {
  let s = 0;
  if (ctx?.stars) s += Math.min(ctx.stars / 1000, 0.3);
  if (ctx?.last_updated) {
    const ageYears = (Date.now() - Date.parse(ctx.last_updated)) / (1000 * 3600 * 24 * 365);
    s += Math.max(0, 0.2 * (1 - ageYears / 5));
  }
  // More heuristics (complexity, patterns) can be appended by worker after static analysis.
  return Math.min(Math.max(s, 0), 1);
}

async function sha256Hex(input: string): Promise<string> {
  const bytes = new TextEncoder().encode(input);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function handlePost(req: Request, url: URL) {
  // Ingestion authentication via shared secret header
  if (!ZENDEXER_INGEST_KEY) {
    return jsonResponse({ error: "server_missing_ingest_key" }, 500);
  }
  const provided = req.headers.get("X-Zendexer-Key") || req.headers.get("x-zendexer-key");
  if (!provided || provided !== ZENDEXER_INGEST_KEY) {
    return jsonResponse({ error: "unauthorized" }, 401);
  }
  // Basic in-memory rate limiting (per key + IP) – best-effort only
  try {
    const ip = (req.headers.get('x-forwarded-for') || '').split(',')[0].trim() || 'unknown';
    const bucketKey = provided + '|' + ip;
    const now = Date.now();
    const arr = rlBuckets.get(bucketKey) || [];
    // prune
    const pruned = arr.filter(ts => now - ts < RATE_LIMIT_WINDOW_MS);
    pruned.push(now);
    rlBuckets.set(bucketKey, pruned);
    if (pruned.length > RATE_LIMIT_MAX) {
      const retryAfter = Math.ceil((RATE_LIMIT_WINDOW_MS - (now - pruned[0]))/1000);
      return new Response(JSON.stringify({ error: 'rate_limited', retry_after_s: retryAfter, window_ms: RATE_LIMIT_WINDOW_MS }), { status: 429, headers: { 'Content-Type':'application/json', 'Retry-After': String(retryAfter), 'Access-Control-Allow-Origin': ALLOWED_ORIGIN }});
    }
  } catch (e) {
    console.warn('[rate-limit] failed', e);
  }
  if (AUTO_CREATE_TABLE) await ensureTableExists(false);
  if (url.searchParams.get("create_table") === "1") await ensureTableExists(true);
  // Persistent window rate limit using log table counts
  try {
    const ipPersist = (req.headers.get('x-forwarded-for') || '').split(',')[0].trim() || 'unknown';
    const windowStartIso = new Date(Date.now() - RATE_LIMIT_WINDOW_MS).toISOString();
    const { data: rlRows, error: rlErr } = await supabase
      .from(LOG_TABLE)
      .select('id')
      .eq('ingest_key', provided)
      .eq('client_ip', ipPersist)
      .gt('created_at', windowStartIso);
    if (!rlErr) {
      const count = rlRows?.length || 0;
      if (count >= RATE_LIMIT_MAX_PERSIST) {
        const retryAfter = Math.ceil(RATE_LIMIT_WINDOW_MS/1000);
        return new Response(JSON.stringify({ error: 'rate_limited', retry_after_s: retryAfter, window_ms: RATE_LIMIT_WINDOW_MS, mode: 'persistent' }), { status: 429, headers: { 'Content-Type':'application/json', 'Retry-After': String(retryAfter), 'Access-Control-Allow-Origin': ALLOWED_ORIGIN }});
      }
    }
  } catch (e) { console.warn('[rate-limit-persist] failed', e); }
  let payload: any;
  try {
    payload = await req.json();
  } catch {
    return jsonResponse({ error: "invalid_json" }, 400);
  }
  const context: ContextMeta | undefined = payload?.context;
  const reqStart = performance.now();
  const ipForLog = (req.headers.get('x-forwarded-for') || '').split(',')[0].trim() || 'unknown';

  // Batch path
  if (Array.isArray(payload?.chunks)) {
    const chunks: QueueInsertSource[] = payload.chunks;
    if (chunks.length > MAX_BATCH_ITEMS) {
      return jsonResponse({ error: "batch_too_large", max: MAX_BATCH_ITEMS }, 413);
    }
    const results: any[] = [];
    for (const c of chunks) {
      const singleStart = performance.now();
      const r = await processSingle(c, context, { allowFetch: true });
      logIngest({
        ingest_key: provided,
        client_ip: ipForLog,
        file_path: c?.file_path,
        repository: c?.repository,
        checksum: r.checksum,
        status: r.error ? 'error' : 'queued',
        error_code: r.error || null,
        bytes: c?.content ? new Blob([c.content]).size : null,
        latency_ms: Math.round(performance.now() - singleStart)
      });
      results.push({ file_path: c?.file_path, repository: c?.repository, ...r });
    }
    return jsonResponse({ results });
  }

  // Single path
  const chunk: QueueInsertSource | undefined = payload?.chunk;
  if (!chunk?.file_path) {
    return jsonResponse({ error: "missing_file_path" }, 422);
  }
  const singleStart = performance.now();
  const result = await processSingle(chunk, context, { allowFetch: true });
  logIngest({
    ingest_key: provided,
    client_ip: ipForLog,
    file_path: chunk.file_path,
    repository: chunk.repository,
    checksum: result.checksum,
    status: result.error ? 'error' : 'queued',
    error_code: result.error || null,
    bytes: chunk.content ? new Blob([chunk.content]).size : null,
    latency_ms: Math.round(performance.now() - singleStart)
  });
  return jsonResponse(result, result.error ? (result.statusCode || 400) : 200);
}

async function handleGet(url: URL) {
  if (AUTO_CREATE_TABLE) await ensureTableExists(false);
  if (url.searchParams.get("create_table") === "1") await ensureTableExists(true);
  // Stats endpoint (authorized via ingest key passed as ?key=)
  if (url.searchParams.get('stats') === '1') {
    const key = url.searchParams.get('key');
    if (!ZENDEXER_INGEST_KEY || key !== ZENDEXER_INGEST_KEY) return jsonResponse({ error: 'unauthorized' }, 401);
    // counts by status
    const { data: counts, error: countsErr } = await supabase
      .from(QUEUE_TABLE)
      .select('status, count:id');
    if (countsErr) return jsonResponse({ error: 'stats_failed', details: countsErr.message }, 500);
    const { data: oldestPending, error: oldestErr } = await supabase
      .from(QUEUE_TABLE)
      .select('created_at')
      .eq('status','pending')
      .order('created_at', { ascending: true })
      .limit(1)
      .maybeSingle();
    let oldest_age_s: number | null = null;
    if (oldestPending?.created_at) {
      try { oldest_age_s = Math.floor((Date.now() - Date.parse(oldestPending.created_at))/1000); } catch {}
    }
    return jsonResponse({ counts: counts || [], oldest_pending_age_s: oldest_age_s });
  }
  const multi = url.searchParams.get("checksums");
  const checksum = url.searchParams.get("checksum");
  if (multi) {
    const list = multi.split(/[,\s]+/).filter(Boolean).slice(0, 50);
    if (!list.length) return jsonResponse({ error: "no_checksums" }, 400);
    const { data, error } = await supabase
      .from(QUEUE_TABLE)
      .select("id,file_path,status,updated_at,error_message,checksum")
      .in("checksum", list);
    if (error) return jsonResponse({ error: "lookup_failed", details: error.message }, 500);
    return jsonResponse({ results: data || [] });
  }
  if (!checksum) return jsonResponse({ error: "missing_checksum" }, 400);
  const { data, error } = await supabase
    .from(QUEUE_TABLE)
    .select("id,file_path,status,updated_at,error_message")
    .eq("checksum", checksum)
    .limit(1)
    .maybeSingle();
  if (error) return jsonResponse({ error: "lookup_failed", details: error.message }, 500);
  if (!data) return jsonResponse({ found: false }, 200);
  return jsonResponse({ found: true, ...data });
}

async function fetchGitHubFile(repository: string, file_path: string, ref?: string): Promise<{ content?: string; error?: string; status?: number; }> {
  if (!repository.includes('/')) return { error: 'invalid_repository' };
  const [owner, repo] = repository.split('/', 2);
  const qs = ref ? `?ref=${encodeURIComponent(ref)}` : '';
  const url = `${GITHUB_API_BASE}/repos/${owner}/${repo}/contents/${encodeURIComponent(file_path)}${qs}`;
  const headers: Record<string,string> = { 'Accept': 'application/vnd.github.raw+json' };
  if (GITHUB_PAT) headers['Authorization'] = `Bearer ${GITHUB_PAT}`;
  const res = await fetch(url, { headers });
  if (res.status === 404) return { error: 'not_found', status: 404 };
  if (!res.ok) return { error: `github_error_${res.status}`, status: res.status };
  const data = await res.json();
  if (data && data.content && data.encoding === 'base64') {
    try {
      const decoded = atob(data.content.replace(/\n/g, ''));
      return { content: decoded };
    } catch {
      return { error: 'decode_failed' };
    }
  }
  // If raw mode responded directly with content
  if (typeof data === 'string') return { content: data };
  return { error: 'unexpected_github_payload' };
}

async function processSingle(chunk: QueueInsertSource, context: ContextMeta | undefined, opts: { allowFetch: boolean }): Promise<any> {
  // Repo allowlist check
  if (chunk.repository && ALLOWED_REPOS.length && !ALLOWED_REPOS.includes(chunk.repository)) {
    return { error: 'repository_not_allowed', repository: chunk.repository, statusCode: 403 };
  }
  let content = chunk.content;
  if (!content && opts.allowFetch && chunk.repository) {
    if (!GITHUB_PAT) {
      return { error: 'missing_github_pat', repository: chunk.repository, file_path: chunk.file_path, statusCode: 401 };
    }
    const fetched = await fetchGitHubFile(chunk.repository, chunk.file_path, (chunk as any).ref);
    if (fetched.error) return { error: fetched.error, repository: chunk.repository, file_path: chunk.file_path, statusCode: fetched.status || 400 };
    content = fetched.content;
  }
  if (!content) return { error: 'missing_content', file_path: chunk.file_path };
  if (new Blob([content]).size > MAX_CONTENT_BYTES) {
    return { error: 'content_too_large', limit: MAX_CONTENT_BYTES, file_path: chunk.file_path, statusCode: 413 };
  }
  const checksum = await sha256Hex(content);
  const confidence = scoreConfidence(chunk, context);
  const { data: existing, error: existingErr } = await supabase
    .from(QUEUE_TABLE)
    .select('id,status')
    .eq('file_path', chunk.file_path)
    .eq('checksum', checksum)
    .limit(1)
    .maybeSingle();
  if (existingErr) return { error: 'lookup_failed', details: existingErr.message, statusCode: 500 };
  if (existing) return { queued: true, checksum, deduplicated: true, status: existing.status };
  const insertRow = {
    file_path: chunk.file_path,
    content,
    language: chunk.language,
    repository: chunk.repository,
    start_line: chunk.start_line,
    end_line: chunk.end_line,
    metadata: chunk.metadata || {},
    checksum,
    confidence_score: confidence,
  status: 'pending',
  commit_sha: (chunk as any).commit_sha || null,
  git_ref: (chunk as any).ref || null
  };
  const { error: insErr } = await supabase.from(QUEUE_TABLE).insert(insertRow);
  if (insErr) return { error: 'queue_insert_failed', details: insErr.message, statusCode: 500 };
  return { queued: true, checksum, confidence };
}

async function logIngest(entry: { ingest_key: string; client_ip: string; file_path?: string; repository?: string; checksum?: string; status: string; error_code?: string | null; bytes?: number | null; latency_ms?: number | null; }) {
  try {
    await supabase.from(LOG_TABLE).insert({
      ingest_key: entry.ingest_key,
      client_ip: entry.client_ip,
      file_path: entry.file_path,
      repository: entry.repository,
      checksum: entry.checksum,
      status: entry.status,
      error_code: entry.error_code,
      bytes: entry.bytes,
      latency_ms: entry.latency_ms
    });
  } catch (e) {
    console.warn('[ingest-log] failed', (e as any)?.message || e);
  }
}

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("", { headers: {
      "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
      "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      "Access-Control-Allow-Methods": "POST,GET,OPTIONS"
    }});
  }
  try {
  const url = new URL(req.url);
  if (req.method === "POST") return await handlePost(req, url);
  if (req.method === "GET") return await handleGet(url);
    return jsonResponse({ error: "method_not_allowed" }, 405);
  } catch (e: any) {
    return jsonResponse({ error: "unhandled_exception", message: e?.message }, 500);
  }
});
