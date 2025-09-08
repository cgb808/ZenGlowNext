<!-- Directory Index: supabase/ -->

# supabase/ Supabase Integration Assets

## Indexed Docs Quick Links

| Area | Doc |
|------|-----|
| Swarm Exploratory Engine | `app/swarm/README.md` |
| Multi-Root Workspace | `docs/MULTI_ROOT_WORKSPACE.md` |
| CUDA Remote Guide | `CUDA_REMOTE_GUIDE.md` |
| File Transfer / Sync | `FILE_TRANSFER_README.md` |
| PII Tagging & Sanitized Export | `docs/PII_TAGGING.md` |
| Governance & RAG (coming) | `docs/` (see future index) |

> Tip: Swarm endpoints (e.g. `/swarm/metrics`) are served by the main FastAPI app; when running via docker-compose use `http://localhost:8001/swarm/metrics`.

Intended for SQL policies, edge functions, or auth integration scaffolding.

Related Docs:

- RLS / security: `../docs/security/RLS_POLICY_REFERENCE.md`

## Added Integrations

- OpenWeatherMap API: endpoints `/weather/current` and `/weather/onecall`
  (requires `OPENWEATHER_API_KEY`).
- Tool Specs endpoint: `/tools/spec` provides machine-readable tool definitions
  (weather tools) for agent/function-calling models.

## Troubleshooting (Quick Wins)

| Issue | Symptom | Resolution |
|-------|---------|------------|
| Missing DB URL | `/ready` shows db.fail or disabled | Set `DATABASE_URL` (or `SUPABASE_DB_URL`), restart. |
| Embed service offline | `/ready` embed.embed_service=fail | Set `EMBED_BASE_URL` or disable retrieval with `RAG_RETRIEVAL_MODE=disabled` temporarily. |
| Invalid retrieval mode | Startup exits config guard | Choose one of `pgvector|weaviate|supabase_rpc|disabled`. |
| Deprecated /model/embed call | 410 Gone | Point clients to remote embed service at `EMBED_BASE_URL`. Enable legacy fallback only with `LEGACY_EMBED=1` + `DEV_LOCAL_EMBED=1` (temporary). |
| Health passes but queries slow | p95 high in logs | Check DB indexing & embedding service latency; inspect `/metrics` counters and add indexing where needed. |
| Unexpected GPU warnings | Logs mention CUDA / NVML on non‑NVIDIA host | Leave GPU probing disabled (default) or unset `ENABLE_GPU_PROBE`; set `ENABLE_GPU_PROBE=1` only on machines with NVIDIA GPUs + GPUtil installed. |

### Environment Validation

Startup config guard fails fast when `STRICT_ENV=true`. To allow degraded startup (dev), set `STRICT_ENV=false`.

### Metrics

Prometheus-style counters available at `/metrics` (minimal scaffold). Future histograms will extend this endpoint without breaking current format.

#### GPU Metrics (Opt-In)

By default the system avoids any GPU / CUDA library probing to keep startup silent on AMD / integrated graphics hosts. To include lightweight GPU utilization and memory stats in `/metrics/sys` set:

```
ENABLE_GPU_PROBE=1
```

Requirements (optional): install `GPUtil` in the environment; absence simply yields an empty `gpus` list. When disabled or unavailable, `"gpus": []` is returned.

### Retention & Maintenance Placeholders

Add to your environment (no logic yet—documentation only):

```
RETENTION_DAYS=30        # Planned: prune old ingestion batches beyond this window
VACUUM_NIGHTLY=true      # Planned: schedule nightly maintenance (pg_cron or external)
```

PostgreSQL maintenance recommendation: run `VACUUM (ANALYZE)` for high-churn tables daily and before large batch ingest jobs.

## 3D Tooling (Streamlit + Three.js)

Experimental lightweight 3D sandbox for Jarvis-style commands lives at `app/tooling/streamlit_threejs_component.py` and Phi demo `app/tooling/streamlit_threejs_phi_demo.py`.

Tool Comparison (lightweight options):
- Three.js (via Streamlit component): Instant, highly interactive, primitives only.
- OpenSCAD: Script-based parametric, needs local binary.
- CADQuery: Pure Python parametric models, good for programmatic assembly.

Run Three.js Phi demo:
```
streamlit run app/tooling/streamlit_threejs_phi_demo.py
```

Planned enhancements:
- Real Phi-3-mini parsing endpoint (extract type/color/size/position)
- Audio (Whisper) -> command pipeline
- Scene export (GLTF/SCAD) and persistence

### Optional Coqui TTS
Install audio extras:
```
pip install -r requirements-audio.txt
```
Endpoints (after install):
- POST /audio/coqui_tts { text, voice?, speaker? }
- GET  /audio/coqui_voices

Env vars:
```
COQUI_VOICE=tts_models/en/vctk/vits
COQUI_SPEAKER_ID=\n```
