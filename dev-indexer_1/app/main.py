"""FastAPI entrypoint for ZenGlow Indexer API.

Startup sequence:
1. Apply env backward compatibility shim.
2. Bootstrap secrets (may populate SUPABASE_KEY).
3. Validate required env vars.
4. Import remainder of modules.
"""

import json
import logging
import os
import pathlib
from collections.abc import Generator
from typing import Any, cast, Dict, List

# Load .env files safely before deeper imports: does not overwrite existing env
try:  # pragma: no cover - early bootstrap
    from scripts.env_load import load_env_files

    load_env_files([".env.local", ".env"])  # order: local overrides base, but no overwrite
except Exception:
    pass

from fastapi import APIRouter, FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# Optional internal imports with safe fallbacks to allow booting with a minimal feature set
try:
    from app.api.openelm_router import router as openelm_router  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub
    openelm_router = APIRouter()

try:
    from app.cache.redis_supabase_cache import (
        get_chunk as cache_get_chunk,
        mget_chunks as cache_mget,
        start_refresh_thread,
    )  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stubs
    def cache_get_chunk(_cid: int):
        return None

    def cache_mget(_ids: list[int]):
        return []

    def start_refresh_thread():  # noqa: D401
        return None

# Core utilities and middleware
try:
    from app.core import log_buffer as _log_buffer  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub buffer
    class _Buf:
        def since(self, _since: int, _limit: int):
            return []

    class _LogBuf:
        def install(self):
            return None

        def get_buffer(self):
            return _Buf()

    _log_buffer = _LogBuf()  # type: ignore

try:  # Prefer new typed metrics facade
    from app.core.metrics_facade import timer as _mf_timer, counter as _mf_counter, observe as _mf_observe  # type: ignore[attr-defined]
    import time as _mt

    class _TimerWrapper:  # pragma: no cover - thin adapter
        def __init__(self):
            self._inner = _mf_timer("request_latency_ms")
            self._start = _mt.time()
        def ms(self) -> float:
            return ( _mt.time() - self._start) * 1000.0
        def stop(self) -> float:
            return self._inner.stop()

    def _m_timer():  # pragma: no cover
        return _TimerWrapper()

    def _m_inc(name: str):  # pragma: no cover
        try:
            _mf_counter(name)
        except Exception:
            pass

    def _m_obs(name: str, val: float):  # pragma: no cover
        try:
            _mf_observe(name, val)
        except Exception:
            pass
except Exception:  # fallback no-ops
    import time as _mt
    class _FallbackTimerWrapper:  # type: ignore
        def __init__(self):
            self._s = _mt.time()
        def ms(self) -> float:
            return (_mt.time() - self._s) * 1000.0
        def stop(self) -> float:
            return self.ms()
    def _m_timer():  # type: ignore  # fallback timer
        return _FallbackTimerWrapper()
    def _m_inc(name: str):  # type: ignore
        return None
    def _m_obs(name: str, val: float):  # type: ignore
        return None

try:
    from app.core.access_log_middleware import AccessLogMiddleware  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - pass-through middleware
    class AccessLogMiddleware(BaseHTTPMiddleware):  # type: ignore
        async def dispatch(self, request, call_next):  # type: ignore[override]
            return await call_next(request)

try:
    from app.core.config import (
        apply_backward_compat_env,
        config_router,
        validate_required_env,
    )  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stubs
    config_router = APIRouter()

    def apply_backward_compat_env():  # type: ignore
        return False

    def validate_required_env():  # type: ignore
        return []

try:
    from app.core.diagnostics_router import router as diagnostics_router  # type: ignore[attr-defined]
except Exception:
    diagnostics_router = APIRouter()

try:
    from app.core import binaries as bin_cache  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub
    class _BinStub:
        def ensure_cached(self, _n: str) -> bool:  # noqa: D401
            return False
        def get_all(self):
            return {}
    bin_cache = _BinStub()  # type: ignore

try:
    from app.core.events_router import router as events_router  # type: ignore[attr-defined]
except Exception:
    events_router = APIRouter()

try:
    from app.core.logging import init_logging, with_ctx  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stubs
    def init_logging():  # type: ignore
        return None

    def with_ctx(logger, **ctx):  # type: ignore
        def _log(msg: str, **kw):
            try:
                logger.debug(msg, extra={**ctx, **kw})
            except Exception:
                pass

        return _log

try:
    from app.core.metrics_endpoint_router import metrics_endpoint_router  # type: ignore[attr-defined]
except Exception:
    metrics_endpoint_router = APIRouter()

try:  # inline lightweight snapshot endpoint if not already provided elsewhere
    from app.core import metrics_facade as _metrics_facade  # type: ignore[attr-defined]
    @metrics_endpoint_router.get("/metrics/snapshot")  # type: ignore[misc]
    async def _metrics_snapshot() -> dict[str, Any]:  # pragma: no cover - simple passthrough
        return _metrics_facade.snapshot()
except Exception:  # pragma: no cover - snapshot unavailable
    pass

try:
    from app.core.metrics_router import router as metrics_router  # type: ignore[attr-defined]
except Exception:
    metrics_router = APIRouter()

try:
    from app.core.secrets import bootstrap_supabase_key  # type: ignore[attr-defined]
except Exception:
    def bootstrap_supabase_key():  # type: ignore
        return None

try:
    from app.core.short_term_memory import GLOBAL_STM  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - minimal STM
    class _STM:
        def __init__(self):
            self._buf: list[tuple[str, str]] = []

        def as_prompt_block(self) -> str:
            parts = [f"{role}: {msg}" for role, msg in self._buf[-6:]]
            return "\n".join(parts)

        def add(self, role: str, msg: str) -> None:
            self._buf.append((role, msg))

    GLOBAL_STM = _STM()  # type: ignore

try:
    from app.core.timescale import ensure_timescale_hypertables  # type: ignore[attr-defined]
except Exception:
    def ensure_timescale_hypertables():  # type: ignore
        return None

# Feature routers
try:
    from app.discovery.router import router as discovery_router  # type: ignore[attr-defined]
except Exception:
    discovery_router = APIRouter()

try:
    from app.feedback.router import router as feedback_router  # type: ignore[attr-defined]
except Exception:
    feedback_router = APIRouter()

try:
    from app.health.health_router import health_router  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - minimal health stub
    health_router = APIRouter()

    @health_router.get("/health")
    async def _health_stub() -> dict[str, Any]:
            # Lazy import for pool stats to avoid import cycles during early bootstrap
            try:
                from app.db.pool import pool_stats  # type: ignore
                _pool = pool_stats()
            except Exception:  # pragma: no cover - defensive
                _pool = {"enabled": False, "error": "unavailable"}
            return {"ok": True, "service": "indexer", "db_pool": _pool}

try:
    # Leonardo analytical audio suite (LLM + TTS + STT)
    from app.audio.leonardo_router import router as leonardo_router  # type: ignore[attr-defined]
except Exception:
    leonardo_router = APIRouter()

try:  # Async transcription jobs router (queue-based)
    from app.audio.transcription_jobs_router import router as transcription_jobs_router  # type: ignore[attr-defined]
except Exception:
    transcription_jobs_router = APIRouter()

try:
    from app.memory import pool as memory_pool  # type: ignore
except Exception:
    class _MemPool:
        def publish_observation(self, **_kw):
            return None

    memory_pool = _MemPool()  # type: ignore

try:
    from app.metrics.metrics_router import metrics_router as ws_metrics_router  # type: ignore[attr-defined]
except Exception:
    ws_metrics_router = APIRouter()

try:
    from app.persona_brightness import (  # type: ignore[attr-defined]
        clamp_level,  # type: ignore
        maybe_add_finisher,  # type: ignore
        infer_brightness as infer_brightness_level,  # type: ignore
    )
except Exception:  # pragma: no cover - stubs
    from typing import Any as _Any

    def clamp_level(x: _Any) -> int | None:  # minimal fallback
        try:
            return int(x)  # type: ignore[arg-type]
        except Exception:
            return None

    def maybe_add_finisher(text: str, _lvl: int | None, phase: str = "closure") -> str:  # noqa: D401
        return text

    def infer_brightness_level(_q: str) -> int:
        return 0

try:
    from app.personas import DEFAULT_PERSONA_KEY, PERSONAS, resolve_persona  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stubs
    DEFAULT_PERSONA_KEY = "default"
    PERSONAS: dict[str, str] = {DEFAULT_PERSONA_KEY: "You are a helpful assistant."}

    def resolve_persona(key: str | None, override: str | None) -> str:  # type: ignore
        return override or PERSONAS.get(key or DEFAULT_PERSONA_KEY, PERSONAS[DEFAULT_PERSONA_KEY])
try:
    from app.core.config import (
        apply_backward_compat_env,
        validate_required_env,
        config_router,
    )  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stubs
    def apply_backward_compat_env() -> bool:  # type: ignore
        return False

    def validate_required_env() -> list[str]:  # type: ignore
        return []

    config_router = APIRouter()

try:
    from app.rag.db_client import DBClient  # type: ignore[import]
except Exception:
    class DBClient:  # type: ignore
        def __init__(self, dsn: str | None = None) -> None:
            self.dsn = dsn

        def fetchall(self, *_a, **_kw):
            return []

        def fetchone(self, *_a, **_kw):
            return None

        def execute(self, *_a, **_kw):
            return None

        def close(self) -> None:
            return None

try:
    from app.rag.edge_llm import get_edge_model_response  # type: ignore[attr-defined]
except Exception:
    def get_edge_model_response(prompt: str) -> str:  # type: ignore
        return "(edge LLM unavailable)"

try:
    from app.rag.embed_router import router as embed_router  # type: ignore[attr-defined]
except Exception:
    embed_router = APIRouter()

try:
    from app.rag.embedder import Embedder  # type: ignore[attr-defined]
except Exception:
    class Embedder:  # type: ignore
        def embed(self, _text: str) -> list[float]:
            return []

try:
    from app.rag.llm_client import LLMClient  # type: ignore[attr-defined]
except Exception:
    class LLMClient:  # type: ignore
        def generate_with_metadata(self, prompt: str, prefer: str = "auto") -> dict[str, Any]:
            return {"text": "(stub answer)", "backend": "stub", "total_latency_ms": 0}

try:
    from app.rag.llm_probe_router import router as llm_probe_router  # type: ignore[attr-defined]
except Exception:
    llm_probe_router = APIRouter()

try:
    from app.rag.pipeline import RAGPipeline  # type: ignore[attr-defined]
except Exception:
    class RAGPipeline:  # type: ignore
        def __init__(self, **_kw):
            pass

        def run(self, query: str, top_k: int = 5) -> str:
            return f"(stub pipeline answer for: {query})"

try:
    from app.rag.ranking_router import (  # type: ignore[attr-defined]
        Query2Payload,
        rag_query2,  # type: ignore
    )
    from app.rag.ranking_router import router as ranking_router  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - minimal stub
    ranking_router = APIRouter()
    async def rag_query2(_payload):  # type: ignore
        return {"results": [], "timings": {}}

try:
    from app.rag.cache_version import get_cache_version  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - stub
    def get_cache_version() -> int:  # type: ignore
        return 0

try:
    from app.rag.rebuild_router import router as rebuild_router  # type: ignore[attr-defined]
except Exception:
    rebuild_router = APIRouter()

try:
    from app.rag.schemas import RAGQueryRequest, RAGQueryResponse  # type: ignore[attr-defined]
except Exception:
    from pydantic import BaseModel

    class RAGQueryRequest(BaseModel):  # type: ignore
        query: str
        top_k: int = 5

    class RAGQueryResponse(BaseModel):  # type: ignore
        answer: str

try:
    from app.rag.streaming_router import router as streaming_router  # type: ignore[attr-defined]
except Exception:
    streaming_router = APIRouter()

try:
    from app.rag.system_router import router as system_rag_router  # type: ignore[attr-defined]
except Exception:
    system_rag_router = APIRouter()

try:
    from app.swarm.state_router import router as swarm_state_router  # type: ignore[attr-defined]
except Exception:
    swarm_state_router = APIRouter()

try:  # optional lightweight predictor
    if os.getenv("SWARM_PREDICT_ENABLE", "1").lower() in {"1", "true", "yes"}:
        from app.swarm.meta_prophet_router import router as swarm_predict_router  # type: ignore[attr-defined]
    else:  # pragma: no cover
        swarm_predict_router = APIRouter()
except Exception:  # pragma: no cover
    swarm_predict_router = APIRouter()

try:  # index-assist helper for Supabase edge functions
    if os.getenv("ASSIST_ENABLE", "1").lower() in {"1", "true", "yes"}:
        from app.rag.index_assist_router import router as index_assist_router  # type: ignore[attr-defined]
    else:  # pragma: no cover
        index_assist_router = APIRouter()
except Exception:  # pragma: no cover
    index_assist_router = APIRouter()

try:
    from app.system.arc_router import router as arc_router  # type: ignore[attr-defined]
except Exception:
    arc_router = APIRouter()

try:  # optional Supabase diagnostics
    from app.integrations.supabase_router import router as supabase_router  # type: ignore[attr-defined]
except Exception:
    supabase_router = APIRouter()

try:  # optional Jarvis inference endpoint
    if os.getenv("JARVIS_ENABLE", "0").lower() in {"1", "true", "yes"}:
        from app.jarvis.router import router as jarvis_router  # type: ignore[attr-defined]
    else:
        jarvis_router = APIRouter()
except Exception:
    jarvis_router = APIRouter()

try:  # optional swarm handlers trainer
    if os.getenv("HANDLERS_ENABLE", "1").lower() in {"1", "true", "yes"}:
        from app.swarm.handlers_router import router as handlers_router  # type: ignore[attr-defined]
    else:
        handlers_router = APIRouter()
except Exception:
    handlers_router = APIRouter()

try:  # optional central control tutor router
    if os.getenv("CENTRAL_ENABLE", "1").lower() in {"1", "true", "yes"}:
        from app.central.router import router as central_router  # type: ignore[attr-defined]
    else:
        central_router = APIRouter()
except Exception:
    central_router = APIRouter()

# Family context (optional)
try:  # type: ignore[attr-defined]
    from app.family.router import router as family_router  # noqa: E402
except Exception:
    family_router = APIRouter()

from app.vector.vector_router import router as vector_router  # type: ignore[attr-defined]

try:  # Optional TTS sidecar proxy
    if os.getenv("TTS_ENABLE", "0").lower() in {"1", "true", "yes"}:
        from app.audio.tts_sidecar_router import router as tts_sidecar_router  # type: ignore  # noqa: E402
    else:  # pragma: no cover - feature flag off
        tts_sidecar_router = None  # type: ignore
except Exception:  # pragma: no cover - defensive
    tts_sidecar_router = None  # type: ignore

# Simple profiles manifest loader (static profile images for dashboard / future RAG enrichment)
_profiles_manifest_path = pathlib.Path("app/static/profile_images/manifest.json")
_profiles: list[dict[str, Any]] = []
try:  # pragma: no cover - I/O path
    if _profiles_manifest_path.exists():
        _profiles = cast(list[dict[str, Any]], json.loads(_profiles_manifest_path.read_text()))
    else:
        _profiles = []
except Exception:  # pragma: no cover - defensive
    _profiles = []

_skip_audio = os.getenv("SKIP_AUDIO_IMPORTS", "0").lower() in {"1", "true", "yes"}
# Auto-skip audio if heavy deps are missing, unless FORCE_AUDIO=1. This lightweight probe
# replaces the older in-module _load_audio() bootstrap (now centralized in app.bootstrap.audio).
if not _skip_audio and os.getenv("FORCE_AUDIO", "0").lower() not in {"1", "true", "yes"}:
    try:  # pragma: no cover - dependency probe
        import importlib

        if importlib.util.find_spec("numpy") is None:  # type: ignore[attr-defined]
            _skip_audio = True
    except Exception:
        pass  # stay optimistic if probe fails


# Use extracted audio bootstrap
from app.bootstrap.audio import load_audio as _bootstrap_load_audio  # type: ignore[attr-defined]

# Centralized audio bootstrap (replaces legacy _load_audio). Returns a dict of optional routers
# and helper objects; all may be None/sentinels depending on env flags and dependency presence.
_AUDIO = _bootstrap_load_audio(_skip_audio)
devices_router = _AUDIO["devices_router"]
transcription_router = _AUDIO["transcription_router"]
tts_router = _AUDIO["tts_router"]
speaker_router = _AUDIO["speaker_router"]
wake_router = _AUDIO["wake_router"]
xtts_router = _AUDIO["xtts_router"]
transcript_enqueue = _AUDIO["transcript_enqueue"]
audio_discovery = _AUDIO["audio_discovery"]
activate_tutor_persona = _AUDIO["activate_tutor_persona"]
get_session_persona = _AUDIO["get_session_persona"]  # type: ignore
piper_router = _AUDIO.get("piper_router")

# Switchr router decoupled from audio gating so predictive tests don't 404 when audio stack skipped
try:  # pragma: no cover - optional import
    from app.central_control.switchr_router import router as switchr_router  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    switchr_router = None  # type: ignore

# Early env + secrets bootstrap so subsequent imports/routers have config
_applied_compat: bool = apply_backward_compat_env()
bootstrap_supabase_key()
try:
    _required_env_missing = validate_required_env()
except Exception:  # pragma: no cover - defensive
    _required_env_missing = []

init_logging()


from typing import Optional as _Opt
from app.db.async_db import init_async_pool, get_async_db_client  # type: ignore[attr-defined]

app_state: dict[str, Any] = {}


@asynccontextmanager
async def _lifespan(app: FastAPI):  # pragma: no cover - runtime path
    # Startup logic (migrated from @app.on_event("startup"))
    log(
        "startup_event",
        applied_compat=_applied_compat,
        required_env_missing=_required_env_missing,
    )
    try:
        ensure_timescale_hypertables()
    except Exception:
        pass
    guard_errors: list[str] = []
    from app.core.config import validate_required_env as _vre  # local import for safety

    missing = _vre()
    if missing:
        guard_errors.append(f"missing_env={','.join(missing)}")
    allowed_modes = {"pgvector", "weaviate", "supabase_rpc", "disabled"}
    mode = os.getenv("RAG_RETRIEVAL_MODE", "pgvector")
    if mode not in allowed_modes:
        guard_errors.append(f"invalid_retrieval_mode={mode}")
    if mode != "disabled" and not os.getenv("EMBED_BASE_URL"):
        os.environ["RAG_RETRIEVAL_MODE"] = "disabled"
        mode = "disabled"
        log("embed_base_url_missing_auto_disabled_retrieval", previous_mode=mode)
    strict = os.getenv("STRICT_ENV", "true").lower() == "true"
    if guard_errors:
        log("startup_config_guard_failed", issues=guard_errors, strict=strict)
        if strict:
            raise SystemExit("config guard failed: " + ";".join(guard_errors))
    else:
        log("startup_config_guard_pass", mode=mode)
    if not _skip_audio:
        try:
            transcript_enqueue.register_persona_callback(activate_tutor_persona)
        except Exception as e:
            log("persona_callback_registration_failed", error=str(e))
        try:
            audio_discovery.start_server()
        except Exception:
            pass
    try:
        start_refresh_thread()
    except Exception:
        log("cache_refresh_thread_start_failed")

    # Initialize async DB pool (Step 1 migration)
    try:
        pool = await init_async_pool()
        if pool:
            app_state["async_db_pool"] = pool
            log("async_db_pool_initialized")
    except Exception as e:  # pragma: no cover - defensive
        log("async_db_pool_init_failed", error=str(e))

    # Optional TinyToolController load
    try:
        import importlib
        mod = importlib.import_module("app.audio.integrated_audio_pipeline")
        TinyToolController = getattr(mod, "TinyToolController", None)
        if TinyToolController:
            app_state["tiny_controller"] = TinyToolController()
            log("tiny_controller_loaded")
        else:
            app_state["tiny_controller"] = None
    except Exception as e:
        app_state["tiny_controller"] = None
        log("tiny_controller_load_failed", error=str(e))
    # Yield to allow application to serve
    yield
    # Shutdown logic (migrated from @app.on_event("shutdown"))
    if not _skip_audio:
        try:
            flushed = transcript_enqueue.flush_pending()
            log("shutdown_flush_transcripts", flushed=flushed)
        except Exception as e:
            log("shutdown_flush_transcripts_error", error=str(e))
    # Close async pool if present
    try:
        pool = app_state.get("async_db_pool")
        if pool:
            await pool.close()  # type: ignore[attr-defined]
            log("async_db_pool_closed")
    except Exception:
        pass
    try:
        log("shutdown_flush_events", forced=True)
    except Exception as e:
        log("shutdown_flush_events_error", error=str(e))


app: FastAPI = FastAPI(title="ZenGlow Indexer API", lifespan=_lifespan)


class CacheVersionHeaderMiddleware(
    BaseHTTPMiddleware
):  # pragma: no cover - simple header injection
    async def dispatch(self, request, call_next):  # type: ignore[override]
        response = await call_next(request)
        try:
            # Only add if not already present
            if "X-Cache-Version" not in response.headers:
                response.headers["X-Cache-Version"] = str(get_cache_version())
        except Exception:
            pass
        return response


app.add_middleware(CacheVersionHeaderMiddleware)

# Access logging middleware (before routers so all routes covered)
app.add_middleware(AccessLogMiddleware)

# CORS (allow configurable origins for local dev / prod UI)
_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_log_buffer.install()  # type: ignore[attr-defined]  # enable in-memory log capture for UI debugging

# Broad callable type (accepts arbitrary structured kwargs)
log = with_ctx(logging.getLogger(__name__), component="startup")
log("app constructing")
app.include_router(health_router)
app.include_router(vector_router)
app.include_router(metrics_endpoint_router)
app.include_router(ranking_router)
app.include_router(rebuild_router)
app.include_router(llm_probe_router)
@app.get("/config/binaries")
def list_binaries() -> dict[str, Any]:  # pragma: no cover - simple
    # Touch a small known set; safe even if absent
    for _b in ("ffmpeg", "sox", "curl"):
        try:
            bin_cache.ensure_cached(_b)
        except Exception:
            pass
    return {"binaries": bin_cache.get_all()}
if not _skip_audio:
    # Unified inclusion loop for audio-related routers (each may either expose .router or be a router itself)
    _audio_candidates = [
        transcription_router,
        tts_router,
        devices_router,
        speaker_router,
        xtts_router,
        piper_router,  # Piper explicitly exposed for clarity
        switchr_router,  # predictive controller (decoupled but related UX-wise)
        wake_router,
    ]
    for _r in _audio_candidates:
        if not _r:
            continue
        try:
            inner = getattr(_r, "router", None)
            app.include_router(inner or _r)  # type: ignore[arg-type]
        except Exception:
            pass
    # Optional dynamically injected coqui_tts_router (legacy experimental)
    try:
        if "coqui_tts_router" in globals() and globals().get("coqui_tts_router"):
            app.include_router(globals()["coqui_tts_router"])  # type: ignore[arg-type]
    except Exception:
        pass
if "tts_sidecar_router" in globals() and tts_sidecar_router:
    app.include_router(tts_sidecar_router)

# Provide /audio/devices and /audio/transcribe even if full audio stack is skipped
if _skip_audio:
    try:
        from app.devices_router import router as simple_devices_router  # type: ignore  # noqa: E402

        app.include_router(simple_devices_router)
    except Exception:
        pass
    try:
        from app.audio.transcription_simple_router import (
            router as transcription_simple_router,
        )  # type: ignore  # noqa: E402

        app.include_router(transcription_simple_router)
    except Exception:
        pass
if os.getenv("SOUND_DIAG_ENABLE", "0").lower() in {"1", "true", "yes"}:
    try:  # pragma: no cover - optional
        from app.audio.audio_diagnostics_router import router as audio_diagnostics_router  # type: ignore  # noqa: E402

        app.include_router(audio_diagnostics_router)
    except Exception:
        pass
app.include_router(leonardo_router)
app.include_router(transcription_jobs_router)
app.include_router(embed_router)
app.include_router(streaming_router)
app.include_router(config_router)
app.include_router(metrics_router)
app.include_router(ws_metrics_router)  # WebSocket metrics streaming
app.include_router(openelm_router)
app.include_router(arc_router)
app.include_router(supabase_router)
app.include_router(discovery_router)
app.include_router(swarm_state_router)
app.include_router(swarm_predict_router)
try:  # optional next-gen swarm router (swarm2)
    from app.swarm2.router import router as swarm2_router  # type: ignore[attr-defined]
    app.include_router(swarm2_router)
except Exception:
    pass
app.include_router(index_assist_router)
app.include_router(jarvis_router)
app.include_router(handlers_router)
app.include_router(central_router)
## app.include_router(achievements_router)
# (specialist_router temporarily disabled / not present)
app.include_router(feedback_router)
app.include_router(system_rag_router)
app.include_router(diagnostics_router)
app.include_router(events_router)
## app.include_router(tooling_router)
## app.include_router(openweather_router)
try:
    from app.swarm.swarm_control_router import router as swarm_control_router  # type: ignore

    app.include_router(swarm_control_router)
except Exception:
    pass
log("routers registered")


# ---------------- Dependency Accessors (importable) -----------------
def get_async_db_client_dep():  # pragma: no cover - thin accessor
    try:
        return get_async_db_client()
    except Exception:
        return None


def get_tiny_controller():  # pragma: no cover
    return app_state.get("tiny_controller")

# ---------------------------------------------------------------------------
# Lightweight Phi-3 status probe (dashboard expects /phi3/ping)
# If an actual dedicated router emerges later, this stub can be removed.
_phi3_router = APIRouter()


@_phi3_router.get("/phi3/ping")
def phi3_ping() -> dict[str, Any]:  # pragma: no cover - trivial
    """Return model readiness/status for dashboard panel.

    Attempts to reflect environment-configured model name; does not perform
    network calls (keeps it cheap for frequent polling). Future enhancement:
    query Ollama /models or backend health when inexpensive.
    """
    model_env = os.getenv("OLLAMA_MODEL") or os.getenv("JARVIS_MODEL") or "phi3:unknown"
    return {
        "model": model_env,
        "status": "ok",  # optimistic stub; refined checks can update
        "backend": "ollama",
        "detail": "stub",
    }


app.include_router(_phi3_router)

# Lightweight governance info endpoint (discoverability for operators)
_gov_router = APIRouter()


@_gov_router.get("/schema/governance")
def schema_governance_info() -> dict[str, Any]:  # pragma: no cover - trivial
    return {
        "docs": {
            "schema_governance": "docs/SCHEMA_GOVERNANCE.md",
            "pii_tagging": "docs/PII_TAGGING.md",
        },
        "tools": {
            "drift_check": "scripts/schema_drift_check.py",
            "sanitized_export": "scripts/schema_export_sanitized.py",
        },
        "supabase": {
            "studio": "https://app.supabase.com/ (project console)",
            "cli": "supabase start / supabase stop (optional local studio)",
        },
    }


app.include_router(_gov_router)

# Static assets (voice UI)
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    # Dedicated mount for dashboard assets when built references absolute /assets path
    assets_dir = "app/static/dashboard/assets"
    if os.path.isdir(assets_dir):  # pragma: no branch
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard_assets")
    try:
        log(
            "static mounts complete",
            assets_dir=assets_dir,
            assets_present=os.path.isdir(assets_dir),
        )
    except Exception:
        pass
except Exception:
    # Directory might not exist in some deploy contexts; fail soft
    pass


def get_rag_pipeline() -> Generator[RAGPipeline, None, None]:
    db_client = DBClient()
    embedder = Embedder()
    llm = LLMClient()
    pipeline = RAGPipeline(db_client=db_client, embedder=embedder, llm_client=llm)  # type: ignore[call-arg]
    try:
        yield pipeline
    finally:
        db_client.close()


@app.get("/profiles", response_class=JSONResponse)
def list_profiles() -> Any:
    """Return static profile image manifest for dashboard consumption."""
    return {"profiles": _profiles, "count": len(_profiles)}


@app.post("/debug/family_adjustment/preview")
async def preview_family_adjustment(payload: dict[str, Any]) -> Any:
    """Debug endpoint to preview adjustment_focus injection (development only)."""
    mode = payload.get("mode")
    prompt = payload.get("prompt", "<empty>")
    ## enriched = fam_maybe_inject(prompt, mode)
    enriched = prompt
    return {
        "input_mode": mode,
        "adjustment_mode_key": None,
        "original": prompt,
        "enriched": enriched,
    }


## (startup/shutdown handlers migrated to lifespan context _lifespan)


@app.post("/rag/query")  # Retrieval + scoring via ranking_router
async def rag_query(request: Request) -> dict[str, Any]:
    total_timer = _m_timer()
    _m_inc("requests_total")
    body = await request.json()
    query = body.get("query")
    top_k = body.get("top_k", 5)
    brightness_override = clamp_level(body.get("persona_brightness"))  # optional
    prefer = body.get("prefer", "auto")  # auto|edge|llama|ollama
    persona_key = body.get("persona_key")  # optional predefined persona key
    session_id = body.get("session_id")  # opaque client-provided id
    # If no explicit persona_key provided, see if session has dynamic tutor persona
    if not persona_key and session_id:
        try:
            dyn_persona = get_session_persona(session_id)
            if dyn_persona and dyn_persona in PERSONAS:
                persona_key = dyn_persona
        except Exception:
            pass
    if not query:
        return {"error": "Missing query"}

    # Reuse rag_query2 internal logic for retrieval + scoring (simulate payload)
    ranking_payload = Query2Payload(query=query, top_k=top_k)
    retrieval_error: str | None = None
    try:
        tmp: Any = await rag_query2(ranking_payload)  # returns dict with results/items
        ranked_dict: dict[str, Any]
        if isinstance(tmp, dict):
            ranked_dict = cast(dict[str, Any], tmp)
        else:
            ranked_dict = {"results": [], "timings": {}}
    except Exception as e:  # graceful fallback: continue with empty context & note error
        ranked_dict = {"results": [], "timings": {}}
        retrieval_error = str(e)
    _m_inc("errors_total")

    # Build answer using fused ranked chunks
    # Normalize typing for strict mode
    if not isinstance(top_k, int):
        try:
            top_k = int(top_k)
        except Exception:
            top_k = 5
    # ranked_dict is ensured above
    results_any: Any = ranked_dict.get("results", [])
    ranked_results: List[Dict[str, Any]] = []
    if isinstance(results_any, list):
        results_list_any: List[Any] = cast(List[Any], results_any)
        for r in results_list_any:
            if isinstance(r, dict):
                d: Dict[str, Any] = cast(Dict[str, Any], r)
                ranked_results.append(d)
    ranked_results = ranked_results[:top_k]
    context = "\n---\n".join([cast(str, r.get("text_preview", "")) for r in ranked_results])
    # Persona resolution (predefined key or env override)
    env_override = os.getenv("ASSISTANT_PERSONA")
    base_persona = resolve_persona(persona_key, env_override)
    safety_tail = " Always be honest about uncertainty. Do not invent citations or sources."  # safety guidance
    persona_full = base_persona + safety_tail
    stm_block = GLOBAL_STM.as_prompt_block()
    if stm_block:
        conversational_context = f"Recent Conversation (most recent last):\n{stm_block}\n---\n"
    else:
        conversational_context = ""
    guidance = (
        "Use the provided context chunks if relevant. If context is empty or "
        "irrelevant, say so briefly and answer from general knowledge if appropriate."
    )
    prompt = (
        f"{persona_full}\n\n{conversational_context}{guidance}\nContext:\n{context}\n"
        f"Question: {query}\nAnswer:"
    )
    # Use unified client; fallback to legacy edge model on error
    llm_client = LLMClient()
    gen_meta: dict[str, Any]
    llm_timer = _m_timer()
    try:
        gen_meta = llm_client.generate_with_metadata(prompt, prefer=prefer)
    except Exception as e:  # pragma: no cover - defensive
        _m_inc("errors_total")
        # Fallback to legacy edge-only path
        answer = get_edge_model_response(prompt)
        gen_meta = {
            "text": answer,
            "backend": "edge_legacy",
            "errors": [str(e)],
        }
    _llm_elapsed_ms = llm_timer.ms()  # reserved for future logging / metrics
    _m_inc("llm_calls_total")

    answer = gen_meta.get("text", "")
    # Update STM with this interaction
    try:
        GLOBAL_STM.add("user", query)
        if answer:
            GLOBAL_STM.add("assistant", answer)
    except Exception:
        pass
    if not answer:
        # Provide a minimal fallback answer so UI doesn't show error blob
        base_fallback = (
            "I can still answer from general knowledge, but retrieval is temporarily unavailable."
            if retrieval_error
            else ""
        )
        answer = base_fallback or "(no answer generated)"
    answer_backend = gen_meta.get("backend")
    answer_latency = gen_meta.get("total_latency_ms")
    answer_errors = gen_meta.get("errors")
    token_estimate = len(answer.split()) if answer else 0
    # Return legacy shape + new scoring metadata
    legacy_chunks = [
        {
            "id": r.get("chunk_id"),
            "chunk": r.get("text_preview"),
            "score": r.get("fused_score"),
            "ltr_score": r.get("ltr_score"),
            "conceptual_score": r.get("conceptual_score"),
            "distance": r.get("distance"),
        }
        for r in ranked_results
    ]
    timings_val: Any = ranked_dict.get("timings", {})
    if isinstance(timings_val, dict):
        timings: Dict[str, Any] = cast(Dict[str, Any], timings_val)
    else:
        timings = cast(Dict[str, Any], {})
    # Observe latency metrics (best-effort); include new per-stage breakdown
    try:
        if timings:
            stage_map = {
                "embed_ms": "embed_ms",
                "retrieve_ms": "retrieval_ms",  # normalize naming
                "feature_ms": "feature_ms",
                "ltr_ms": "ltr_ms",
                "fusion_ms": "fusion_ms",
                "total_ms": "pipeline_ms",
            }
            for src_key, metric_key in stage_map.items():
                val = timings.get(src_key)
                if val is not None:
                    try:
                        _m_obs(metric_key, float(val))
                    except Exception:
                        pass
        if answer_latency is not None:
            try:
                _m_obs("llm_ms", float(answer_latency))
            except Exception:
                pass
        # Overall end-to-end (from request ingress to response build)
        try:
            _m_obs("total_ms", total_timer.ms())
        except Exception:
            pass
    except Exception:
        pass

    # Determine brightness (use override or infer from user query)
    try:
        if brightness_override is not None:
            brightness_level = brightness_override
        else:
            brightness_level = infer_brightness_level(query or "")
        answer = maybe_add_finisher(answer, brightness_level, phase="closure")
        brightness_int: int | None = int(brightness_level)
    except Exception:
        brightness_int = None

    result_obj: dict[str, Any] = {
        "chunks": legacy_chunks,
        "answer": answer,
        "answer_meta": {
            "backend": answer_backend,
            "latency_ms": answer_latency,
            "token_estimate": token_estimate,
            "errors": answer_errors,
            "prefer": prefer,
            "persona_key": persona_key or ("env_override" if env_override else DEFAULT_PERSONA_KEY),
            "retrieval_error": retrieval_error,
            "rag_used": retrieval_error is None and len(legacy_chunks) > 0,
            "timings": timings,
            "brightness": brightness_int,
        },
        "fusion_weights": ranked_dict.get("fusion_weights"),
        "feature_schema_version": ranked_dict.get("feature_schema_version"),
        "feature_names": ranked_dict.get("feature_names"),
        "scoring_version": ranked_dict.get("scoring_version"),
        "session_id": session_id,
    }
    # Opportunistic fine-tune capture (non-blocking best-effort)
    try:
        # Placeholder: fine-tune capture disabled (original call commented out)
        # capture_example(query, answer, legacy_chunks, result_obj["answer_meta"])
        pass
    except Exception:
        pass
    # Emit exploration observation (low-impact): average fused score as quality heuristic
    try:
        if os.getenv("MEMORY_ENABLE", "0") in {"1", "true", "yes"}:
            fused_scores = [c.get("score") or c.get("ltr_score") or 0.0 for c in legacy_chunks]
            avg_score = sum(fused_scores) / len(fused_scores) if fused_scores else 0.0
            _pub = getattr(memory_pool, "publish_observation", None)
            if callable(_pub):
                _pub(
                    kind="rag_answer",
                    payload={"q": query[:120], "len": len(answer), "k": len(legacy_chunks)},
                    score=min(0.99, max(0.0, avg_score / 10.0)),  # scale into 0-~0.1 then clamp
                    source="rag_query",
                )
    except Exception:
        pass
    return result_obj

    # unreachable


@app.get("/swarm/status")
def swarm_status() -> dict[str, Any]:  # pragma: no cover - simple
    try:
        from app.swarm.ant_swarm import export_pheromones  # type: ignore
    except Exception:
        return {"enabled": False}
    sample_any: Any = cast(Any, export_pheromones(limit=20))
    return {
        "enabled": os.getenv("ENABLE_SWARM", "0"),
        "edges_sample": sample_any,
        "fine_tune_capture": None,
    }


@app.get("/memory/status")
def memory_status() -> dict[str, Any]:  # pragma: no cover - lightweight
    try:
        from app.memory.pool import list_recent  # type: ignore
    except Exception:
        return {"enabled": False}
    recent_any: Any = cast(Any, list_recent(10))
    return {"enabled": os.getenv("MEMORY_ENABLE", "0"), "recent": recent_any}


@app.get("/cache/chunk/{cid}")
def cache_chunk_lookup(cid: int) -> dict[str, Any]:  # pragma: no cover - simple
    meta = cache_get_chunk(cid)
    if not meta:
        try:
            from app.cache.redis_supabase_cache import fetch_and_cache_chunk  # type: ignore

            meta = fetch_and_cache_chunk(cid)
        except Exception:
            meta = None
    return {"id": cid, "meta": meta}


@app.post("/cache/chunks")
async def cache_chunks_lookup(payload: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
    ids_raw: Any = payload.get("ids")
    ids: list[int] = []
    if isinstance(ids_raw, list):
        ids_list_any: List[Any] = cast(List[Any], ids_raw)
        for x in ids_list_any:
            try:
                ids.append(int(x))
            except Exception:
                continue
    metas = cache_mget(ids)
    return {"items": metas}


@app.get("/config/personas")
def list_personas() -> dict[str, Any]:
    return {"personas": list(PERSONAS.keys()), "default": DEFAULT_PERSONA_KEY}


@app.get("/audio/discover")
def audio_discover() -> dict[str, Any]:  # lightweight broadcast scan
    try:
        return {"services": audio_discovery.client_scan()}
    except Exception:
        return {"services": []}


@app.get("/dashboard")
def dashboard_page():
    """Serve built React dashboard (copied into app/static/dashboard)."""
    path = "app/static/dashboard/index.html"
    if os.path.exists(path):  # pragma: no branch
        return FileResponse(path)
    return {"error": "dashboard_not_found"}


@app.get("/")
def root_redirect():  # pragma: no cover - simple redirect
    return RedirectResponse(url="/dashboard")


@app.get("/logs/recent")
def logs_recent(since: int = 0, limit: int = 400) -> dict[str, Any]:
    """Return recent log lines since id (polling model)."""
    buf = _log_buffer.get_buffer()
    lines = buf.since(since, limit)
    next_id = lines[-1]["id"] if lines else since
    return {"lines": lines, "next": next_id}


@app.post("/rag/pipeline", response_model=RAGQueryResponse)
async def rag_pipeline_endpoint(payload: RAGQueryRequest) -> RAGQueryResponse:
    # Acquire a pipeline instance explicitly (Avoid Depends function call in default)
    for pipeline in get_rag_pipeline():  # generator yields then finally closes
        run = getattr(pipeline, "run", None)
        if callable(run):
            try:
                answer_any: Any = run(query=payload.query, top_k=payload.top_k)
                answer_str = str(answer_any) if answer_any is not None else ""
                return RAGQueryResponse(answer=answer_str)
            except Exception:
                return RAGQueryResponse(answer="(pipeline error)")
        return RAGQueryResponse(answer="(pipeline available, run() missing)")
    # Fallback (should not happen)
    return RAGQueryResponse(answer="(pipeline unavailable)")
