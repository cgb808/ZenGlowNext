from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests

from app.core import metrics
from app.rag.llm_backend_registry import list_backends  # new pluggable backend registry


# Defensive no-op wrappers so tests run even if metrics facade not fully implemented
def _m_inc(name: str) -> None:  # pragma: no cover - trivial guard
    try:  # type: ignore[attr-defined]
        metrics.inc(name)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def _m_obs(name: str, value: float) -> None:  # pragma: no cover - trivial guard
    try:  # type: ignore[attr-defined]
        metrics.observe(name, value)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def _resolve_supabase_key() -> Optional[str]:
    return (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )


log = logging.getLogger("app.rag.llm_client")


class LLMClient:
    # Whether outbound calls to non-local hosts are allowed (set at init)
    _allow_external: bool = False

    def __init__(
        self,
        default_temperature: float = 0.2,
        max_timeout_seconds: int = 120,
        retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        self.default_temperature = default_temperature
        self.max_timeout_seconds = max_timeout_seconds
        self.retries = retries
        self.backoff_base = backoff_base
        self._session = requests.Session()
        # Outbound allow strategy:
        # 1. If LLM_ALLOW_EXTERNAL=1 -> no restriction (use with care)
        # 2. Otherwise we allow localhost, 127.*, and RFC1918 LAN ranges (10.*, 192.168.*, 172.16-31.*)
        # 3. Additional prefixes may be supplied via LLM_ALLOW_PREFIXES (comma separated, exact startswith match)
        self._allow_external = os.getenv("LLM_ALLOW_EXTERNAL", "0").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        extra_prefixes_raw = os.getenv("LLM_ALLOW_PREFIXES", "")
        self._allow_prefixes = [
            p.strip() for p in extra_prefixes_raw.split(",") if p.strip()
        ]
        # Precompute base safe prefixes (when _allow_external is False)
        self._local_prefixes = [
            "http://localhost",
            "https://localhost",
            "http://127.",
            "https://127.",
            "http://10.",
            "https://10.",
            "http://192.168.",
            "https://192.168.",
            # 172.16. -> 172.31.
            *[f"http://172.{i}." for i in range(16, 32)],
            *[f"https://172.{i}." for i in range(16, 32)],
        ]

    # Public API -----------------------------------------------------------
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 512,
        prefer: str = "auto",  # auto|edge|llama|ollama
    ) -> str:
        return self.generate_with_metadata(
            prompt, temperature=temperature, max_tokens=max_tokens, prefer=prefer
        ).get("text", "")

    def generate_with_metadata(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 512,
        prefer: str = "auto",  # auto|edge|llama|ollama|leonardo|leo|jarvis|mistral|phi3
    ) -> Dict[str, Any]:
        _m_inc("llm_calls_total")
        debug = os.getenv("LLM_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
        if debug:
            log.debug(
                "llm.generate.start",
                extra={
                    "prefer": prefer,
                    "max_tokens": max_tokens,
                    "len_prompt": len(prompt),
                },
            )
        temp = temperature if temperature is not None else self.default_temperature

        # Preference override
        force_prefer = os.getenv("LLM_FORCE_PREFER", "").strip().lower()
        if force_prefer:
            prefer = force_prefer
        elif (prefer or "").strip().lower() in {"", "auto"}:
            default_prefer = os.getenv("LLM_DEFAULT_PREFER", "").strip().lower()
            if default_prefer:
                prefer = default_prefer

        # Disabled backends
        disabled_raw = os.getenv("LLM_DISABLE", "")
        disabled_tokens = [d.strip().lower() for d in disabled_raw.split(",") if d.strip()]
        if any(tok in {"all", "*", "true", "1"} for tok in disabled_tokens):
            disabled: set[str] = {"edge", "ollama", "llama", "llama.cpp"}
        else:
            disabled = set(disabled_tokens)
        if {"edge", "ollama", "llama", "llama.cpp"}.issubset(disabled):
            if debug:
                log.warning("llm.all_disabled", extra={"disabled": list(disabled)})
            return {
                "backend": "disabled",
                "text": "",
                "errors": ["all llm backends disabled via LLM_DISABLE"],
                "total_latency_ms": 0.0,
                "disabled": True,
            }

        errors: list[str] = []
        start_total = time.time()
        for backend_func in list_backends():
            meta = backend_func(
                self, prompt, temp, max_tokens, prefer, disabled, errors, start_total, debug
            )
            if meta is not None:
                return meta
            if prefer != "auto" and backend_func.__name__.endswith(prefer.replace(".", "_")):
                break

        if prefer in {"edge", "ollama", "llama", "leonardo", "jarvis", "mistral", "phi3"} and errors:
            total_ms = (time.time() - start_total) * 1000
            _m_obs("llm_total_latency_ms", total_ms)
            if os.getenv("DEV_FAKE_LLM", "false").lower() == "true":
                lower = prompt.lower()
                idx = lower.rfind("question:")
                question = prompt[idx + 9 :].strip() if idx != -1 else prompt[-160:]
                if len(question) > 160:
                    question = question[-160:]
                fake = f"[DEV FAKE ANSWER] {question[:200]}"
                return {
                    "backend": "dev_fake",
                    "text": fake,
                    "errors": errors,
                    "total_latency_ms": total_ms,
                }
            return {
                "backend": None,
                "text": "",
                "errors": errors,
                "total_latency_ms": total_ms,
            }

        total_ms = (time.time() - start_total) * 1000
        if debug:
            log.error("llm.all_failed", extra={"errors": errors})
        _m_obs("llm_total_latency_ms", total_ms)
        backend = None
        text = ""
        if os.getenv("DEV_FAKE_LLM", "false").lower() == "true":
            lower = prompt.lower()
            idx = lower.rfind("question:")
            question = prompt[idx + 9 :].strip() if idx != -1 else prompt[-160:]
            if len(question) > 160:
                question = question[-160:]
            text = f"[DEV FAKE ANSWER] {question[:200]}"
            backend = "dev_fake"
        return {
            "backend": backend,
            "text": text,
            "errors": errors or ["no backend succeeded"],
            "total_latency_ms": total_ms,
        }

    # --- Internal helpers -------------------------------------------------
    def _invoke_edge(
        self,
        base_url: Optional[str],
        fn_name: str,
        key: Optional[str],
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[Optional[str], Dict[str, Any]]:
        if not base_url or not key:
            return None, {"error": "edge not configured"}
        fn_url = f"{base_url.rstrip('/')}/functions/v1/{fn_name}"
        # Outbound safety: block non-local unless explicitly allowed
        if not self._allow_external and not fn_url.startswith(
            tuple(self._local_prefixes + self._allow_prefixes)
        ):
            return None, {"error": "blocked outbound (edge)"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }
        last_error: Optional[str] = None
        start = time.time()
        for attempt in range(self.retries + 1):
            try:
                resp = self._session.post(
                    fn_url,
                    json={
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=self.max_timeout_seconds,
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = (
                        data.get("output")
                        or data.get("response")
                        or data.get("text")
                        or (data if isinstance(data, str) else str(data))
                    )
                    return text, {
                        "latency_ms": (time.time() - start) * 1000,
                        "attempts": attempt + 1,
                        "status_code": resp.status_code,
                    }
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as e:  # noqa: BLE001
                last_error = f"exception: {type(e).__name__}: {e}"
            if attempt < self.retries:
                time.sleep(self.backoff_base * (2**attempt))
        return None, {
            "error": last_error or "unknown edge failure",
            "latency_ms": (time.time() - start) * 1000,
            "attempts": self.retries + 1,
        }

    def _invoke_ollama(
        self,
        base_url: str,
        model: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[Optional[str], Dict[str, Any]]:
        url = f"{base_url.rstrip('/')}/api/generate"
        if not self._allow_external and not url.startswith(
            tuple(self._local_prefixes + self._allow_prefixes)
        ):
            return None, {"error": "blocked outbound (ollama)"}
        start = time.time()
        try:
            resp = self._session.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "options": {"temperature": temperature},
                    "stream": False,
                },
                timeout=self.max_timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("response")
                or data.get("output")
                or data.get("text")
                or (data if isinstance(data, str) else str(data))
            )
            return text, {
                "latency_ms": (time.time() - start) * 1000,
                "status_code": resp.status_code,
            }
        except Exception as e:  # noqa: BLE001
            return None, {
                "error": f"ollama exception: {type(e).__name__}: {e}",
                "latency_ms": (time.time() - start) * 1000,
            }

    def _invoke_llama_cpp(
        self,
        server_url: Optional[str],
        model_path: Optional[str],
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[Optional[str], Dict[str, Any]]:
        """Invoke llama.cpp HTTP server (future: direct mode)."""
        if not server_url and not model_path:
            return None, {"error": "llama.cpp not configured"}
        if server_url:
            url = f"{server_url.rstrip('/')}/completion"
            if not self._allow_external and not url.startswith(
                tuple(self._local_prefixes + self._allow_prefixes)
            ):
                return None, {"error": "blocked outbound (llama.cpp)"}
            start = time.time()
            try:
                resp = self._session.post(
                    url,
                    json={
                        "prompt": prompt,
                        "temperature": temperature,
                        "n_predict": max_tokens,
                    },
                    timeout=self.max_timeout_seconds,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = (
                        data.get("content")
                        or data.get("completion")
                        or data.get("response")
                        or data.get("text")
                        or (data if isinstance(data, str) else str(data))
                    )
                    return text, {
                        "latency_ms": (time.time() - start) * 1000,
                        "status_code": resp.status_code,
                    }
                return None, {
                    "error": f"llama.cpp HTTP {resp.status_code}: {resp.text[:160]}",
                    "latency_ms": (time.time() - start) * 1000,
                    "status_code": resp.status_code,
                }
            except Exception as e:  # noqa: BLE001
                return None, {
                    "error": f"llama.cpp exception: {type(e).__name__}: {e}",
                    "latency_ms": (time.time() - start) * 1000,
                }
        return None, {"error": "llama.cpp server_url not set"}
