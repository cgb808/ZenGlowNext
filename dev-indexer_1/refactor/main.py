"""FastAPI entrypoint for ZenGlow Indexer API.
Order of operations on import:
    1. Apply env backward compatibility shim (old -> new names).
    2. Bootstrap secrets (may populate SUPABASE_KEY).
    3. Validate required env vars (fail fast if missing).
Then import remainder of modules relying on configuration.
"""

import logging
import os
from typing import Any, Dict, Generator

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core import log_buffer as _log_buffer
from app.core.config import (apply_backward_compat_env, config_router,
                             validate_required_env)
from app.core.diagnostics_router import router as diagnostics_router
from app.core.logging import init_logging, with_ctx
from app.core.metrics_router import router as metrics_router
from app.core.secrets import bootstrap_supabase_key
from app.health.health_router import health_router
from app.personas import DEFAULT_PERSONA_KEY, PERSONAS, resolve_persona
from app.agents.stoic_agent import StoicAgent
try:
    from app.core.persona_tone import build_persona_suffix
except Exception:
    build_persona_suffix = None  # graceful fallback if module missing
from app.core.mood_state import (
    detect_mood_command,
    get_mood,
    set_mood,
    mood_style_instructions,
)
from app.rag.schemas import RAGQueryRequest, RAGQueryResponse

# 1. Backward compatibility env translation
_applied_compat = apply_backward_compat_env()
# 2. Load Supabase indexer key early (may populate SUPABASE_KEY from Vault)
bootstrap_supabase_key()
# 3. Validate required envs (raises RuntimeError if missing)
try:
    validate_required_env(fail_fast=True)
except RuntimeError:  # pragma: no cover - startup failure path
    # Re-raise to prevent app from starting with invalid config
    raise

from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from app.audio import devices_router, transcription_router, tts_router
from app.audio.speaker_router import router as speaker_router
from app.audio.wake_router import router as wake_router
from app.audio.xtts_router import router as xtts_router
from app.central_control.switchr_router import router as switchr_router
from app.central_control.voice_fragment_router import router as voice_fragment_router
from app.core import metrics as inproc_metrics
from app.leonardo.audio_router import router as leonardo_router
from app.metrics.metrics_router import metrics_router as ws_metrics_router
from app.swarm.router import router as swarm_router
from app.rag.db_client import DBClient
from app.core.lifespan import lifespan as combined_lifespan
# Legacy imports (can be deprecated once new pipeline stable)
# Legacy direct embedding/retrieval removed; use ranking_router logic instead. Edge LLM kept for answer generation.
from app.rag.edge_llm import get_edge_model_response  # Legacy fallback
from app.rag.embed_router import router as embed_router
from app.rag.embedder import Embedder
from app.rag.llm_client import LLMClient
from app.rag.llm_probe_router import router as llm_probe_router
from app.rag.pipeline import RAGPipeline
from app.rag.ranking_router import (  # reuse logic for legacy endpoint refactor
    Query2Payload, rag_query2)
from app.rag.ranking_router import router as ranking_router
from app.rag.streaming_router import \
    router as streaming_router  # SSE phased diff (Artifact D)
from app.nlp.router import router as nlp_router
from app.agents.clarification import select_clarification
from app.assistant.intent_classifier import classify_intent, MED_THRESHOLD, AMBIG_LOW
from app.integrations.pubmed import get_pubmed_evidence, format_evidence_for_prompt

init_logging()
# Always provide a lifespan that conditionally initializes optional resources
app: FastAPI = FastAPI(title="ZenGlow Indexer API", lifespan=combined_lifespan)
_log_buffer.install()  # enable in-memory log capture for UI debugging
log = with_ctx(logging.getLogger(__name__), component="startup")
log("app constructing")
app.include_router(health_router)
app.include_router(ranking_router)
app.include_router(llm_probe_router)
app.include_router(transcription_router.router)
app.include_router(tts_router.router)
app.include_router(devices_router.router)
app.include_router(speaker_router)
app.include_router(xtts_router)
app.include_router(leonardo_router)
app.include_router(switchr_router)
app.include_router(voice_fragment_router)
app.include_router(wake_router)
app.include_router(embed_router)
app.include_router(streaming_router)
app.include_router(nlp_router)
app.include_router(config_router)
app.include_router(metrics_router)
app.include_router(ws_metrics_router)  # WebSocket metrics streaming
app.include_router(diagnostics_router)
app.include_router(swarm_router)
log("routers registered")

# Static assets (voice UI)
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    # Dedicated mount for dashboard assets when built references absolute /assets path
    assets_dir = "app/static/dashboard/assets"
    if os.path.isdir(assets_dir):  # pragma: no branch
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard_assets")
    log(
        "static mounts complete",
        assets_dir=assets_dir,
        assets_present=os.path.isdir(assets_dir),
    )
except Exception:
    # Directory might not exist in some deploy contexts; fail soft
    pass


def get_rag_pipeline() -> Generator[RAGPipeline, None, None]:
    db_client = DBClient()
    embedder = Embedder()
    llm = LLMClient()
    pipeline = RAGPipeline(db_client=db_client, embedder=embedder, llm_client=llm)
    try:
        yield pipeline
    finally:
        db_client.close()

# ---------------- Intent Classification Endpoint -----------------
from pydantic import BaseModel as _BM  # local alias to avoid confusion
class IntentRequest(_BM):
    text: str

class IntentResponse(_BM):
    domain: str
    confidence: float
    reasons: list[str]
    threshold_medical: float
    threshold_ambiguous: float

@app.post("/intent/classify", response_model=IntentResponse)
async def intent_classify(req: IntentRequest) -> IntentResponse:
    if not req.text.strip():  # fast path
        return IntentResponse(domain="general", confidence=0.0, reasons=[], threshold_medical=MED_THRESHOLD, threshold_ambiguous=AMBIG_LOW)
    # Feature flag optional (INTENT_GATE_ENABLED=1) else still expose low-risk
    res = classify_intent(req.text)
    return IntentResponse(domain=res.domain, confidence=res.confidence, reasons=res.reasons, threshold_medical=MED_THRESHOLD, threshold_ambiguous=AMBIG_LOW)


# Startup logging now handled during construction and via lifespan, avoiding deprecated on_event.


@app.post(
    "/rag/query"
)  # Refactored legacy endpoint: delegates scoring to /rag/query2 logic; now supports backend preference
async def rag_query(request: Request) -> Dict[str, Any]:
    total_timer = inproc_metrics.Timer()
    inproc_metrics.inc("requests_total")
    body = await request.json()
    query = body.get("query")
    top_k = body.get("top_k", 5)
    prefer = body.get("prefer", "auto")  # auto|edge|llama|ollama
    persona_key = body.get("persona_key")  # optional predefined persona key
    session_id = body.get("session_id")  # opaque client-provided id
    user_id = body.get("user_id")  # optional user for mood scoping
    if not query:
        return {"error": "Missing query"}

    intent_meta = None
    _intent = None
    if os.getenv("INTENT_GATE_ENABLED", "1") == "1":  # default on for enrichment
        _intent = classify_intent(query)
        intent_meta = {
            "domain": _intent.domain,
            "confidence": _intent.confidence,
            "reasons": _intent.reasons,
            "medical_threshold": MED_THRESHOLD,
            "ambiguous_threshold": AMBIG_LOW,
            "route_recommendation": ("pubmed_model" if _intent.confidence >= MED_THRESHOLD else ("clarify" if _intent.confidence >= AMBIG_LOW else "general_model")),
        }
        # Optional: proactively route to a clarifier when intent is ambiguous.
        # Disabled by default to avoid changing legacy behavior; enable with INTENT_CLARIFY_ROUTE=1
        if (
            os.getenv("INTENT_CLARIFY_ROUTE", "0") == "1"
            and AMBIG_LOW <= float(_intent.confidence) < MED_THRESHOLD
        ):
            clar = select_clarification(query, {})
            clar_text = (
                clar.get("clarification_prompt")
                if isinstance(clar, dict)
                else None
            ) or "Quick check: what’s the core goal and one constraint?"
            return {
                "chunks": [],
                "answer": clar_text,
                "answer_meta": {
                    "clarification": True,
                    "clarification_band": (clar.get("band") if isinstance(clar, dict) else None),
                    "clarification_confidence": (clar.get("confidence") if isinstance(clar, dict) else None),
                    "intent": intent_meta,
                    "prefer": "auto",
                    "rag_used": False,
                },
                "session_id": session_id,
            }

    mood_cmd = detect_mood_command(query)  # e.g., "set your mood to bright"
    if mood_cmd:
        ack = set_mood(mood_cmd, session_id=session_id, user_id=user_id)
        return {
            "answer": ack,
            "answer_meta": {
                "persona_key": persona_key or DEFAULT_PERSONA_KEY,
                "mood": mood_cmd,
                "mood_command": True,
                "intent": intent_meta,
            },
            "chunks": [],
        }

    # Reuse rag_query2 internal logic for retrieval + scoring (simulate payload)
    route_hint = None
    # Allow clients to suggest a route and optionally infer from intent if enabled
    if os.getenv("DB_ROUTE_ENABLED", "0") == "1":
        rh = (body.get("route_hint") or "").strip().lower()
        if rh in ("pii", "specialist", "general"):
            route_hint = rh
        elif _intent is not None and float(_intent.confidence) >= MED_THRESHOLD:
            route_hint = "specialist"  # medical intent -> specialist DB by default
    ranking_payload = Query2Payload(query=query, top_k=top_k, route_hint=route_hint)
    retrieval_error: str | None = None
    try:
        ranked = await rag_query2(ranking_payload)  # returns dict with results/items
    except (
        Exception
    ) as e:  # graceful fallback: continue with empty context & note error
        ranked = {"results": [], "timings": {}}
        retrieval_error = str(e)
        inproc_metrics.inc("errors_total")

    # Build answer using fused ranked chunks
    ranked_results = ranked.get("results", [])[:top_k]
    context_chunks = [r.get("text_preview", "") for r in ranked_results]

    # Optional PubMed augmentation when intent is strongly medical
    used_pubmed = False
    pubmed_records = []
    if (
        os.getenv("PUBMED_ENABLE", "0") == "1"
        and _intent is not None
        and float(_intent.confidence) >= MED_THRESHOLD
    ):
        try:
            pubmed_records = get_pubmed_evidence(query, max_results=min(5, top_k or 5))
            if pubmed_records:
                used_pubmed = True
                context_chunks.append("PubMed Evidence:\n" + format_evidence_for_prompt(pubmed_records))
        except Exception:
            # Non-fatal; continue without PubMed
            pass

    context = "\n---\n".join([c for c in context_chunks if c])
    # Persona resolution (predefined key or env override)
    env_override = os.getenv("ASSISTANT_PERSONA")
    base_persona = resolve_persona(persona_key, env_override)
    safety_tail = " Always be honest about uncertainty. Do not invent citations or sources."  # short safety guidance
    current_mood = get_mood(session_id=session_id, user_id=user_id)
    mood_instr = mood_style_instructions(current_mood)
    # Dynamic tone blending for jarvis_2 persona
    tone_suffix = ""
    if 'jarvis_2' in (persona_key or '') and build_persona_suffix:
        tone_context = {
            "user_text": query,
            # Placeholders for future instrumentation (stress metrics, etc.)
            "hrv_stress_score": body.get("hrv_stress_score"),
            "emotional_language": body.get("emotional_language"),
            "task_type": body.get("task_type"),
        }
        try:
            tone_suffix = "\n" + build_persona_suffix(tone_context)
        except Exception:
            tone_suffix = ""
    persona_full = base_persona + " " + mood_instr + safety_tail + tone_suffix
    prompt = (
        f"{persona_full}\n\n"
        f"Use the provided context chunks if relevant. If context is empty or irrelevant, say so briefly and answer from general knowledge if appropriate."
        f"\nIf mood is bright you may insert ONE mid-sentence courteous flourish (e.g., ', if I may, sir,') at most once, never at the beginning or end."
        f"\nContext:\n{context}\nQuestion: {query}\nAnswer:"
    )
    # Prefer new unified client so user can experiment with backends; fallback to legacy if generation fails
    llm_client = LLMClient()
    gen_meta: Dict[str, Any]
    llm_timer = inproc_metrics.Timer()
    try:
        gen_meta = llm_client.generate_with_metadata(prompt, prefer=prefer)
    except Exception as e:  # pragma: no cover - defensive
        inproc_metrics.inc("errors_total")
        # Fallback to legacy edge-only path
        answer = get_edge_model_response(prompt)
        gen_meta = {"text": answer, "backend": "edge_legacy", "errors": [str(e)]}
    llm_elapsed = llm_timer.ms()
    inproc_metrics.inc("llm_calls_total")

    answer = gen_meta.get("text", "")
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
    timings = ranked.get("timings", {}) or {}
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
                        inproc_metrics.observe(metric_key, float(val))
                    except Exception:
                        pass
        if answer_latency is not None:
            try:
                inproc_metrics.observe("llm_ms", float(answer_latency))
            except Exception:
                pass
        # Overall end-to-end (from request ingress to response build)
        try:
            inproc_metrics.observe("total_ms", total_timer.ms())
        except Exception:
            pass
    except Exception:
        pass

    response_payload = {
        "chunks": legacy_chunks,
        "answer": answer,
        "answer_meta": {
            "backend": answer_backend,
            "latency_ms": answer_latency,
            "token_estimate": token_estimate,
            "errors": answer_errors,
            "prefer": prefer,
            "intent": intent_meta,
            "persona_key": persona_key
            or ("env_override" if env_override else DEFAULT_PERSONA_KEY),
            "mood": current_mood if 'current_mood' in locals() else None,
            "retrieval_error": retrieval_error,
            "rag_used": retrieval_error is None and len(legacy_chunks) > 0,
            "timings": timings,
            "pubmed_used": used_pubmed,
        },
        "fusion_weights": ranked.get("fusion_weights"),
        "feature_schema_version": ranked.get("feature_schema_version"),
        "feature_names": ranked.get("feature_names"),
        "scoring_version": ranked.get("scoring_version"),
        "session_id": session_id,
    }

    # Attach lightweight PubMed citations to answer_meta if available
    if used_pubmed and pubmed_records:
        try:
            response_payload["answer_meta"]["pubmed_citations"] = [
                {"pmid": r.pmid, "title": r.title, "journal": r.journal, "year": r.year, "url": r.url}
                for r in pubmed_records
            ]
        except Exception:
            pass
    return response_payload


@app.get("/config/personas")
def list_personas():
    return {"personas": list(PERSONAS.keys()), "default": DEFAULT_PERSONA_KEY}


stoic_agent = StoicAgent()


@app.post("/agent/stoic/assist")
async def stoic_assist(payload: dict):
    """Lightweight endpoint: provide stoic tiered guidance if activation criteria met.

    Expects: {"query": str, "confidence": float (optional), "user_id": str (optional)}
    Returns: {"activated": bool, "response": str | None, "tiered": bool}
    """
    user_query = payload.get("query") or ""
    confidence = float(payload.get("confidence", 0.7))
    ctx = {"user_id": payload.get("user_id","anonymous")}
    result = stoic_agent.respond(user_query, ctx, confidence)
    return {"activated": result is not None, "response": result, "tiered": bool(result)}


@app.post("/agent/stoic/commit_step")
async def stoic_commit_step(payload: dict):
    step = payload.get('step') or ''
    if not step:
        return {"error": "missing step"}
    ctx = {"user_id": payload.get("user_id","anonymous")}
    res = stoic_agent.commit_step(step, ctx)
    return {"ok": True, "committed": res is not None}


@app.post("/agent/stoic/thanks_check")
async def stoic_thanks_check(payload: dict):
    text = payload.get('text') or ''
    return {"positive_followup": stoic_agent.detect_positive_followup(text)}


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
def logs_recent(since: int = 0, limit: int = 400):
    """Return recent log lines since id (polling model)."""
    buf = _log_buffer.get_buffer()
    lines = buf.since(since, limit)
    next_id = lines[-1]["id"] if lines else since
    return {"lines": lines, "next": next_id}


class FamilyAdjustmentPreviewRequest(BaseModel):
    mode: str = "adjustment_focus"
    prompt: str
    persona_hint: str | None = None
    include_supporting: bool = True


@app.post("/debug/family_adjustment/preview")
async def family_adjustment_preview(payload: FamilyAdjustmentPreviewRequest):
    """Return a synthetic preview response illustrating adjustment_focus contextualization.

    This mirrors dataset injection logic (Amy + Bella 12 + Connor 14 relocating from South Charleston, WV).
    """
    base_prompt = payload.prompt.strip()
    relocation_note = (
        "Relocation context: Nancy's sister Amy and her children Bella (12) and Connor (14) recently moved in from South Charleston, West Virginia just before the school term; both are anxious and warming up socially."
    )
    support_tail = (
        "Support lens: acknowledge Bella's princess energy while offering gentle structure; engage Connor through outdoor / fishing aligned metaphors to build trust."
    )
    clarifier = (
        "If any part of this guidance misses what you hoped for, share one concrete detail (e.g., mood this morning, a small win, a friction point) and I'll refine."  # no trailing punctuation duplication
    )
    response_parts = [
        f"Prompt: {base_prompt}",
        relocation_note,
    ]
    if payload.include_supporting:
        response_parts.extend([
            "Adjustment phase: early-to-stabilizing; emotions: anxious → cautious optimism.",
            support_tail,
            clarifier,
        ])
    synthetic_answer = "\n\n".join(response_parts)
    return {
        "mode": payload.mode,
        "input_prompt": base_prompt,
        "synthetic_answer": synthetic_answer,
        "family_adjustment": {
            "new_members": ["amy_sister", "bella_amy_child", "connor_amy_child"],
            "relocation_origin": "South Charleston, WV",
            "emotions": ["anxious", "nervous", "warming_up"],
        },
    }


class ClarificationRequest(BaseModel):
    user_input: str
    hrv: float | None = None
    user_id: str | None = None
    session_id: str | None = None


@app.post("/agent/clarify")
async def agent_clarify(payload: ClarificationRequest):
    """Return confidence + optional clarification prompt.

    Lightweight heuristic layer bridging to dataset's inferred_confidence pattern.
    """
    ctx = {}
    if payload.hrv is not None:
        ctx["hrv"] = payload.hrv
    result = select_clarification(payload.user_input, ctx)
    return result


@app.post("/rag/pipeline", response_model=RAGQueryResponse)
async def rag_pipeline_endpoint(
    payload: RAGQueryRequest, pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> RAGQueryResponse:
    answer = pipeline.run(query=payload.query, top_k=payload.top_k)
    # For now we don't surface chunk scores since db_client stub doesn't provide them
    return RAGQueryResponse(answer=answer, chunks=[])
