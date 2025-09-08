"""
Embedding client with explicit runtime modes and fallbacks.

Goals:
- No heavy deps (no transformers/torch required) in default path.
- Primary path: HTTP endpoint defined by EMBED_ENDPOINT returning {"embeddings": [[...]]} for {"texts": [...]}
- Fallback: Supabase Edge Function when EMBED_MODE=supabase (or EMBED_SUPABASE_FUNCTION is set)
- Last resort: cheap deterministic hash embedding (dev only)

Environment:
- EMBED_MODE: "http" (default) | "supabase" | "disabled"
- EMBED_ENDPOINT: URL for HTTP embed service (default: http://127.0.0.1:8000/model/embed)
- EMBED_HTTP_TIMEOUT: seconds (default: 15)
- SUPABASE_URL, SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY
- EMBED_SUPABASE_FUNCTION: edge function name (default: embed)
- EMBED_SUPABASE_PATH: full path override (e.g., /functions/v1/custom-embed)
- EMBED_FALLBACK_CHEAP: 1 to allow deterministic cheap embedding fallback (default: 1)

Contract:
- embed(text) -> List[float]
- embed_batch(texts) -> List[List[float]] (keeps order; empty inputs -> [])

Error handling:
- If mode="disabled" -> raises RuntimeError
- If HTTP/Supabase fail and fallback disabled -> re-raise last error
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import List, cast

import requests


def _cheap_embed(text: str, dim: int = 384) -> List[float]:
	h = hashlib.sha256(text.encode("utf-8")).digest()
	raw = (h * ((dim // len(h)) + 1))[:dim]
	vec = [((b / 255.0) * 2.0 - 1.0) for b in raw]
	norm = math.sqrt(sum(v * v for v in vec)) or 1.0
	return [v / norm for v in vec]


class Embedder:
	def __init__(self) -> None:
		self.mode = os.getenv("EMBED_MODE", "http").lower()
		self.endpoint = os.getenv("EMBED_ENDPOINT", "http://127.0.0.1:8000/model/embed")
		self.timeout = float(os.getenv("EMBED_HTTP_TIMEOUT", "15"))
		self.allow_cheap = os.getenv("EMBED_FALLBACK_CHEAP", "1").lower() in {"1", "true", "yes"}

		# Supabase settings
		self.supabase_url = os.getenv("SUPABASE_URL")
		self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
		self.supabase_fn = os.getenv("EMBED_SUPABASE_FUNCTION", "embed")
		self.supabase_path = os.getenv("EMBED_SUPABASE_PATH")  # if provided, overrides /functions/v1/<fn>

	def embed(self, text: str) -> List[float]:
		if not text:
			return []
		return self.embed_batch([text])[0]

	def embed_batch(self, texts: List[str]) -> List[List[float]]:
		if not texts:
			return []
		mode = self.mode
		last_err: Exception | None = None

		if mode == "disabled":
			raise RuntimeError("Embedding disabled by EMBED_MODE=disabled")

		# 1) Supabase Edge-first if explicitly requested
		if mode == "supabase":
			try:
				return self._embed_supabase(texts)
			except Exception as e:
				last_err = e
				# fall through -> HTTP -> cheap

		# 2) HTTP endpoint (default)
		try:
			return self._embed_http(texts)
		except Exception as e:
			last_err = e

		# 3) Supabase as fallback when mode=http but env present
		if self.supabase_url and self.supabase_key:
			try:
				return self._embed_supabase(texts)
			except Exception as e:
				last_err = e

		# 4) Cheap deterministic fallback (dev only)
		if self.allow_cheap:
			return [_cheap_embed(t) for t in texts]

		# If we get here, re-raise the last error
		if last_err:
			raise last_err
		raise RuntimeError("Embedding failed with no fallback available")

	# --- Internal helpers ---
	def _embed_http(self, texts: List[str]) -> List[List[float]]:
		url = self.endpoint
		resp = requests.post(url, json={"texts": texts}, timeout=self.timeout)
		resp.raise_for_status()
		data = resp.json()
	embeddings = data.get("embeddings")
	if not isinstance(embeddings, list):
			raise ValueError("Invalid embedding response: missing 'embeddings'")
	return cast(List[List[float]], embeddings)

	def _embed_supabase(self, texts: List[str]) -> List[List[float]]:
		if not (self.supabase_url and self.supabase_key):
			raise RuntimeError("Supabase credentials missing for embedding fallback")
		if self.supabase_path:
			path = self.supabase_path
			if not path.startswith("/"):
				path = "/" + path
			url = f"{self.supabase_url.rstrip('/')}{path}"
		else:
			url = f"{self.supabase_url.rstrip('/')}/functions/v1/{self.supabase_fn}"
		headers = {
			"apikey": self.supabase_key,
			"Authorization": f"Bearer {self.supabase_key}",
			"Content-Type": "application/json",
		}
		body = {"texts": texts}
		resp = requests.post(url, json=body, headers=headers, timeout=self.timeout)
		resp.raise_for_status()
	data = resp.json()
	embeddings = data.get("embeddings")
	if not isinstance(embeddings, list):
			raise ValueError("Invalid Supabase embedding response: missing 'embeddings'")
	return cast(List[List[float]], embeddings)

