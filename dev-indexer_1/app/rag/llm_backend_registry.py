"""Pluggable LLM backend registry.

Each backend attempt function receives the LLMClient instance plus invocation
parameters and either returns a populated metadata dict (including backend,
text, total_latency_ms, errors) or None if that backend should be skipped or
failed.

The registry keeps ordering stable; new backends can be appended without
modifying `llm_client.py` core logic.
"""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

from app.core import metrics

BackendFunc = Callable[[Any, str, float, int, str, set[str], List[str], float, bool], Optional[Dict[str, Any]]]

_REGISTRY: List[BackendFunc] = []


def register_backend(func: BackendFunc) -> BackendFunc:
    _REGISTRY.append(func)
    return func


def list_backends() -> List[BackendFunc]:  # pragma: no cover - trivial
    return list(_REGISTRY)


@register_backend
def attempt_edge(
    client: Any,
    prompt: str,
    temperature: float,
    max_tokens: int,
    prefer: str,
    disabled: set[str],
    errors: List[str],
    start_total: float,
    debug: bool,
) -> Optional[Dict[str, Any]]:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    multi_fn_raw = os.getenv("SUPABASE_EDGE_FUNCTIONS")
    if multi_fn_raw:
        supabase_functions = [f.strip() for f in multi_fn_raw.split(",") if f.strip()]
    else:
        supabase_functions = [os.getenv("SUPABASE_EDGE_FUNCTION", "get_gemma_response")]
    attempt_edge = (
        prefer in ("auto", "edge") and bool(supabase_url and supabase_key) and "edge" not in disabled
    )
    if not attempt_edge:
        return None
    for fn_name in supabase_functions:
        txt, meta = client._invoke_edge(  # type: ignore[attr-defined]
            supabase_url,
            fn_name,
            supabase_key,
            prompt,
            temperature,
            max_tokens,
        )
        if txt is not None:
            total_ms = (time.time() - start_total) * 1000
            metrics.observe("llm_total_latency_ms", total_ms)  # type: ignore[attr-defined]
            metrics.observe("llm_edge_latency_ms", meta.get("latency_ms", 0))  # type: ignore[attr-defined]
            meta.update(
                {
                    "backend": "edge",
                    "text": txt,
                    "function": fn_name,
                    "total_latency_ms": total_ms,
                    "errors": errors,
                }
            )
            return meta
        err_msg = meta.get("error", "failure")
        errors.append(f"{fn_name}: {err_msg}")
    # No success; caller handles explicit prefer failure path
    return None


@register_backend
def attempt_llama_cpp(
    client: Any,
    prompt: str,
    temperature: float,
    max_tokens: int,
    prefer: str,
    disabled: set[str],
    errors: List[str],
    start_total: float,
    debug: bool,
) -> Optional[Dict[str, Any]]:
    server_url = os.getenv("LLAMA_CPP_SERVER_URL")
    model_path = os.getenv("LLAMA_CPP_MODEL")
    attempt = prefer in ("auto", "llama") and server_url and "llama" not in disabled
    if not attempt:
        return None
    txt, meta = client._invoke_llama_cpp(  # type: ignore[attr-defined]
        server_url, model_path, prompt, temperature, max_tokens
    )
    if txt is not None:
        total_ms = (time.time() - start_total) * 1000
        metrics.observe("llm_total_latency_ms", total_ms)  # type: ignore[attr-defined]
        metrics.observe("llm_llama_latency_ms", meta.get("latency_ms", 0))  # type: ignore[attr-defined]
        meta.update(
            {
                "backend": "llama.cpp",
                "text": txt,
                "errors": errors,
                "total_latency_ms": total_ms,
            }
        )
        return meta
    llama_err = meta.get("error", "llama.cpp: failure")
    errors.append(llama_err)
    return None


@register_backend
def attempt_ollama(
    client: Any,
    prompt: str,
    temperature: float,
    max_tokens: int,
    prefer: str,
    disabled: set[str],
    errors: List[str],
    start_total: float,
    debug: bool,
) -> Optional[Dict[str, Any]]:
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma:2b")
    attempt = prefer in ("auto", "ollama") and "ollama" not in disabled
    if not attempt:
        return None
    txt, meta = client._invoke_ollama(  # type: ignore[attr-defined]
        ollama_url, ollama_model, prompt, temperature, max_tokens
    )
    if txt is not None:
        total_ms = (time.time() - start_total) * 1000
        metrics.observe("llm_total_latency_ms", total_ms)  # type: ignore[attr-defined]
        metrics.observe("llm_ollama_latency_ms", meta.get("latency_ms", 0))  # type: ignore[attr-defined]
        meta.update(
            {
                "backend": "ollama",
                "text": txt,
                "errors": errors,
                "total_latency_ms": total_ms,
            }
        )
        return meta
    errors.append(meta.get("error", "ollama: failure"))
    return None


@register_backend
def attempt_leonardo(
    client: Any,
    prompt: str,
    temperature: float,
    max_tokens: int,
    prefer: str,
    disabled: set[str],
    errors: List[str],
    start_total: float,
    debug: bool,
) -> Optional[Dict[str, Any]]:
    if prefer == "leo":  # alias normalization
        prefer = "leonardo"
    if prefer not in ("leonardo", "mistral") or "ollama" in disabled:
        return None
    url = os.getenv("LEONARDO_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
    model = os.getenv("LEONARDO_MODEL", "mistral:7b")
    txt, meta = client._invoke_ollama(  # type: ignore[attr-defined]
        url, model, prompt, temperature, max_tokens
    )
    if txt is not None:
        total_ms = (time.time() - start_total) * 1000
        metrics.observe("llm_total_latency_ms", total_ms)  # type: ignore[attr-defined]
        metrics.observe("llm_leonardo_latency_ms", meta.get("latency_ms", 0))  # type: ignore[attr-defined]
        meta.update(
            {
                "backend": "leonardo",
                "text": txt,
                "errors": errors,
                "total_latency_ms": total_ms,
            }
        )
        return meta
    errors.append(meta.get("error", "leonardo: failure"))
    return None


@register_backend
def attempt_jarvis(
    client: Any,
    prompt: str,
    temperature: float,
    max_tokens: int,
    prefer: str,
    disabled: set[str],
    errors: List[str],
    start_total: float,
    debug: bool,
) -> Optional[Dict[str, Any]]:
    if prefer not in ("jarvis", "phi3") or "ollama" in disabled:
        return None
    url = os.getenv("JARVIS_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
    model = os.getenv("JARVIS_MODEL", "phi3:3.8b-mini-4k-instruct-q4_0")
    txt, meta = client._invoke_ollama(  # type: ignore[attr-defined]
        url, model, prompt, temperature, max_tokens
    )
    if txt is not None:
        total_ms = (time.time() - start_total) * 1000
        metrics.observe("llm_total_latency_ms", total_ms)  # type: ignore[attr-defined]
        metrics.observe("llm_jarvis_latency_ms", meta.get("latency_ms", 0))  # type: ignore[attr-defined]
        meta.update(
            {
                "backend": "jarvis",
                "text": txt,
                "errors": errors,
                "total_latency_ms": total_ms,
            }
        )
        return meta
    errors.append(meta.get("error", "jarvis: failure"))
    return None
