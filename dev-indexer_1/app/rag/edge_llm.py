"""
Supabase Edge Function integration for ZenGlow RAG pipeline.
Used for egress (LLM generation or data retrieval).
"""

import os

from supabase import Client, create_client

_supabase_client: Client | None = None


def _get_client() -> Client | None:
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL")
    key_candidates = [
        os.environ.get("SUPABASE_SERVICE_KEY"),
        os.environ.get("SUPABASE_KEY"),
        os.environ.get("SUPABASE_ANON_KEY"),
    ]
    key = next((k for k in key_candidates if k), None)
    if not url or not key:
        return None
    try:
        _supabase_client = create_client(url, key)
    except Exception:  # pragma: no cover - network
        _supabase_client = None
    return _supabase_client


EDGE_FUNCTION_NAME = os.environ.get("SUPABASE_EDGE_FUNCTION", "get_gemma_response")


def get_edge_model_response(prompt: str) -> str:
    client = _get_client()
    if not client:
        return "(edge backend not configured)"
    try:
        response = client.functions.invoke(
            EDGE_FUNCTION_NAME,
            invoke_options={
                "body": {"prompt": prompt},
                "headers": {"Content-Type": "application/json"},
            },
        )
        data = getattr(response, "data", response)
        return data if isinstance(data, str) else str(data)
    except Exception as e:  # noqa: BLE001
        return f"(edge error: {e.__class__.__name__})"
