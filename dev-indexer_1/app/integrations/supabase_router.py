from __future__ import annotations

"""Supabase integration diagnostics router.

Provides quick checks to validate configuration and reachability for Supabase
Edge Functions and PostgREST RPC without tight coupling to core flows.
"""

import os
from typing import Any, Dict

import requests
from fastapi import APIRouter


router = APIRouter(prefix="/supabase", tags=["supabase"])


@router.get("/config")
def supabase_config() -> Dict[str, Any]:  # pragma: no cover - trivial
    present = {k: bool(os.getenv(k)) for k in ("SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY")}
    # don't leak values; just presence flags
    return {
        "url": bool(os.getenv("SUPABASE_URL")),
        "key": any(present[k] for k in ("SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY")),
        "edge_function": os.getenv("SUPABASE_EDGE_FUNCTION", "get_gemma_response"),
        "rpc_fn": os.getenv("SUPABASE_SIM_SEARCH_RPC", "match_documents"),
    }


@router.get("/rpc/ping")
def supabase_rpc_ping() -> Dict[str, Any]:
    base_url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not base_url or not key:
        return {"attempted": False, "ok": False, "reason": "missing url/key"}
    fn = os.getenv("SUPABASE_HEALTH_RPC", "health_ping")
    url = f"{base_url.rstrip('/')}/rest/v1/rpc/{fn}"
    headers = {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "return=representation",
    }
    try:
        resp = requests.post(url, json={}, headers=headers, timeout=int(os.getenv("SUPABASE_TIMEOUT", "10")))
        ok = resp.status_code == 200
        body = None
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:200]
        return {"attempted": True, "ok": ok, "status": resp.status_code, "body": body}
    except Exception as e:  # pragma: no cover - defensive
        return {"attempted": True, "ok": False, "error": str(e)}
