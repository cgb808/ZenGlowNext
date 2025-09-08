from __future__ import annotations

"""LLM backend probe endpoint.

Lightweight reachability / quick-response check for configured backends so the UI
can explain why answers are empty (e.g. all backends failing silently).

Does short generation attempts with a minimal prompt and captures error messages.
No caching; intended for ad-hoc diagnostics (not high frequency polling).
"""

import os
import time

from fastapi import APIRouter

from app.rag.llm_client import LLMClient

router = APIRouter(prefix="/llm", tags=["llm"])

_PING_PROMPT = "System probe: respond with a single word 'ok'."


def _probe_edge(client: LLMClient) -> dict:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not (supabase_url and supabase_key):
        return {"attempted": False, "ok": False, "reason": "supabase creds missing"}
    t0 = time.time()
    try:
        meta = client.generate_with_metadata(_PING_PROMPT, max_tokens=4, prefer="edge")
        ok = bool(meta.get("text")) and meta.get("backend") == "edge"
        return {
            "attempted": True,
            "ok": ok,
            "latency_ms": (time.time() - t0) * 1000,
            "backend": meta.get("backend"),
            "errors": meta.get("errors"),
        }
    except Exception as e:  # pragma: no cover - defensive
        return {"attempted": True, "ok": False, "error": str(e)}


def _probe_ollama(client: LLMClient) -> dict:
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    if not ollama_url:
        return {"attempted": False, "ok": False, "reason": "OLLAMA_URL unset"}
    t0 = time.time()
    try:
        meta = client.generate_with_metadata(
            _PING_PROMPT, max_tokens=4, prefer="ollama"
        )
        ok = bool(meta.get("text")) and meta.get("backend") == "ollama"
        return {
            "attempted": True,
            "ok": ok,
            "latency_ms": (time.time() - t0) * 1000,
            "backend": meta.get("backend"),
            "errors": meta.get("errors"),
        }
    except Exception as e:
        return {"attempted": True, "ok": False, "error": str(e)}


def _probe_llama_cpp(client: LLMClient) -> dict:
    url = os.getenv("LLAMA_CPP_SERVER_URL")
    if not url:
        return {"attempted": False, "ok": False, "reason": "LLAMA_CPP_SERVER_URL unset"}
    t0 = time.time()
    try:
        meta = client.generate_with_metadata(_PING_PROMPT, max_tokens=4, prefer="llama")
        ok = bool(meta.get("text")) and meta.get("backend") in ("llama.cpp", "llama")
        return {
            "attempted": True,
            "ok": ok,
            "latency_ms": (time.time() - t0) * 1000,
            "backend": meta.get("backend"),
            "errors": meta.get("errors"),
        }
    except Exception as e:
        return {"attempted": True, "ok": False, "error": str(e)}


@router.get("/probe")
def probe_llms() -> dict:
    client = LLMClient()
    edge = _probe_edge(client)
    ollama = _probe_ollama(client)
    llama_cpp = _probe_llama_cpp(client)
    return {
        "edge": edge,
        "ollama": ollama,
        "llama_cpp": llama_cpp,
        "all_failed": all(
            not v.get("ok") for v in [edge, ollama, llama_cpp] if v.get("attempted")
        ),
    }


__all__ = ["router"]
