from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests

from app.core import metrics


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
        metrics.inc("llm_calls_total")
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

        # Env resolution
        supabase_url = os.getenv("SUPABASE_URL")
        multi_fn_raw = os.getenv("SUPABASE_EDGE_FUNCTIONS")
        if multi_fn_raw:
            supabase_functions = [
                f.strip() for f in multi_fn_raw.split(",") if f.strip()
            ]
        else:
            supabase_functions = [
                os.getenv("SUPABASE_EDGE_FUNCTION", "get_gemma_response")
            ]
        supabase_key = _resolve_supabase_key()

        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "gemma:2b")
        llama_cpp_model_path = os.getenv(
            "LLAMA_CPP_MODEL"
        )  # placeholder future direct mode
        llama_cpp_server_url = os.getenv("LLAMA_CPP_SERVER_URL")

        # Disable list (comma separated): entries can include 'edge','ollama','llama', or special values: all,* ,true,1
        disabled_raw = os.getenv("LLM_DISABLE", "")
        disabled_tokens = [
            d.strip().lower() for d in disabled_raw.split(",") if d.strip()
        ]
        if any(tok in {"all", "*", "true", "1"} for tok in disabled_tokens):
            disabled: set[str] = {"edge", "ollama", "llama", "llama.cpp"}
        else:
            disabled = set(disabled_tokens)

        # If every backend disabled, return early consistent structure
        if {"edge", "ollama", "llama", "llama.cpp"}.issubset(disabled):
            if debug:
                log.warning("llm.all_disabled", extra={"disabled": list(disabled)})
            total_ms = 0.0
            return {
                "backend": "disabled",
                "text": "",
                "errors": ["all llm backends disabled via LLM_DISABLE"],
                "total_latency_ms": total_ms,
                "disabled": True,
            }

        attempt_edge = (
            prefer in ("auto", "edge")
            and bool(supabase_url and supabase_key)
            and "edge" not in disabled
        )
        errors: list[str] = []
        start_total = time.time()

        # 1. Supabase Edge
        if attempt_edge:
            if debug:
                log.debug("llm.attempt.edge", extra={"functions": supabase_functions})
            for fn_name in supabase_functions:
                txt, meta = self._invoke_edge(
                    supabase_url, fn_name, supabase_key, prompt, temp, max_tokens
                )
                if txt is not None:
                    if debug:
                        log.info(
                            "llm.success.edge",
                            extra={
                                "function": fn_name,
                                "latency_ms": meta.get("latency_ms"),
                            },
                        )
                    total_ms = (time.time() - start_total) * 1000
                    metrics.observe("llm_total_latency_ms", total_ms)
                    metrics.observe("llm_edge_latency_ms", meta.get("latency_ms", 0))
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
                errors.append(f"{fn_name}: " + err_msg)
                if debug:
                    log.warning(
                        "llm.fail.edge",
                        extra={
                            "function": fn_name,
                            "error": err_msg,
                            "attempts": meta.get("attempts"),
                        },
                    )
            if prefer == "edge":
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                if os.getenv("DEV_FAKE_LLM", "false").lower() == "true":
                    lower = prompt.lower()
                    idx = lower.rfind("question:")
                    question = prompt[idx + 9 :].strip() if idx != -1 else prompt[-160:]
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

        # 2. llama.cpp server (if configured)
        if (
            prefer in ("auto", "llama")
            and llama_cpp_server_url
            and "llama" not in disabled
        ):
            if debug:
                log.debug(
                    "llm.attempt.llama_cpp", extra={"server": llama_cpp_server_url}
                )
            txt, meta = self._invoke_llama_cpp(
                llama_cpp_server_url, llama_cpp_model_path, prompt, temp, max_tokens
            )
            if txt is not None:
                if debug:
                    log.info(
                        "llm.success.llama_cpp",
                        extra={"latency_ms": meta.get("latency_ms")},
                    )
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                metrics.observe("llm_llama_latency_ms", meta.get("latency_ms", 0))
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
            if debug:
                log.warning("llm.fail.llama_cpp", extra={"error": llama_err})
            if prefer == "llama":
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                if os.getenv("DEV_FAKE_LLM", "false").lower() == "true":
                    lower = prompt.lower()
                    idx = lower.rfind("question:")
                    question = prompt[idx + 9 :].strip() if idx != -1 else prompt[-160:]
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

        # 3. Ollama
        if prefer in ("auto", "ollama") and "ollama" not in disabled:
            if debug:
                log.debug(
                    "llm.attempt.ollama",
                    extra={"url": ollama_url, "model": ollama_model},
                )
            txt, meta = self._invoke_ollama(
                ollama_url, ollama_model, prompt, temp, max_tokens
            )
            if txt is not None:
                if debug:
                    log.info(
                        "llm.success.ollama",
                        extra={"latency_ms": meta.get("latency_ms")},
                    )
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                metrics.observe("llm_ollama_latency_ms", meta.get("latency_ms", 0))
                meta.update(
                    {
                        "backend": "ollama",
                        "text": txt,
                        "errors": errors,
                        "total_latency_ms": total_ms,
                    }
                )
                return meta
            ollama_err = meta.get("error", "ollama: failure")
            errors.append(ollama_err)
            if debug:
                log.warning("llm.fail.ollama", extra={"error": ollama_err})
            if prefer == "ollama":
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                if os.getenv("DEV_FAKE_LLM", "false").lower() == "true":
                    lower = prompt.lower()
                    idx = lower.rfind("question:")
                    question = prompt[idx + 9 :].strip() if idx != -1 else prompt[-160:]
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

        # Normalize alias 'leo' -> 'leonardo'
        if prefer == "leo":
            prefer = "leonardo"

        # 4. Leonardo (Mistral 7B on RTX 3060 Ti)
        if prefer in ("leonardo", "mistral") and "ollama" not in disabled:
            leonardo_url = os.getenv("LEONARDO_URL", ollama_url)
            leonardo_model = os.getenv("LEONARDO_MODEL", "mistral:7b")
            if debug:
                log.debug(
                    "llm.attempt.leonardo",
                    extra={"url": leonardo_url, "model": leonardo_model},
                )
            txt, meta = self._invoke_ollama(
                leonardo_url, leonardo_model, prompt, temp, max_tokens
            )
            if txt is not None:
                if debug:
                    log.info(
                        "llm.success.leonardo",
                        extra={"latency_ms": meta.get("latency_ms")},
                    )
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                metrics.observe("llm_leonardo_latency_ms", meta.get("latency_ms", 0))
                meta.update(
                    {
                        "backend": "leonardo",
                        "text": txt,
                        "errors": errors,
                        "total_latency_ms": total_ms,
                    }
                )
                return meta
            leonardo_err = meta.get("error", "leonardo: failure")
            errors.append(leonardo_err)
            if debug:
                log.warning("llm.fail.leonardo", extra={"error": leonardo_err})

        # 5. Jarvis (Phi3 on GTX 1660 Super)
        if prefer in ("jarvis", "phi3") and "ollama" not in disabled:
            jarvis_url = os.getenv("JARVIS_URL", ollama_url)
            jarvis_model = os.getenv("JARVIS_MODEL", "phi3:3.8b-mini-4k-instruct-q4_0")
            if debug:
                log.debug(
                    "llm.attempt.jarvis",
                    extra={"url": jarvis_url, "model": jarvis_model},
                )
            txt, meta = self._invoke_ollama(
                jarvis_url, jarvis_model, prompt, temp, max_tokens
            )
            if txt is not None:
                if debug:
                    log.info(
                        "llm.success.jarvis",
                        extra={"latency_ms": meta.get("latency_ms")},
                    )
                total_ms = (time.time() - start_total) * 1000
                metrics.observe("llm_total_latency_ms", total_ms)
                metrics.observe("llm_jarvis_latency_ms", meta.get("latency_ms", 0))
                meta.update(
                    {
                        "backend": "jarvis",
                        "text": txt,
                        "errors": errors,
                        "total_latency_ms": total_ms,
                    }
                )
                return meta
            jarvis_err = meta.get("error", "jarvis: failure")
            errors.append(jarvis_err)
            if debug:
                log.warning("llm.fail.jarvis", extra={"error": jarvis_err})

        # Failure path (optionally fake answer in dev)
        total_ms = (time.time() - start_total) * 1000
        if debug:
            log.error("llm.all_failed", extra={"errors": errors})
        metrics.observe("llm_total_latency_ms", total_ms)
        text = ""
        backend = None
        if os.getenv("DEV_FAKE_LLM", "false").lower() == "true":
            # Derive a short fake answer from prompt
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
