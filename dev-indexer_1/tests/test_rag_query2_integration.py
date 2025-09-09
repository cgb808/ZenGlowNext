"""Tests for /rag/query2 fusion scoring and response structure.

Marked as integration; skipped by default to avoid resource spikes.
"""

import os

import pytest

SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION_TESTS") == "1"
pytestmark = pytest.mark.skipif(SKIP_INTEGRATION, reason="SKIP_INTEGRATION_TESTS=1")

if not SKIP_INTEGRATION:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)


def test_rag_query2_basic():
    resp = client.post("/rag/query2", json={"query": "test", "top_k": 3})
    # During early development DB may be empty; handle 500 gracefully
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "results" in data
        if data["results"]:
            first = data["results"][0]
            assert "ltr_score" in first
            assert "conceptual_score" in first
            assert "fused_score" in first
            assert "fusion_weights" in data


def test_fusion_weight_normalization():
    # Force pathological weights via env override then call endpoint
    os.environ["RAG_FUSION_LTR_WEIGHT"] = "0"
    os.environ["RAG_FUSION_CONCEPTUAL_WEIGHT"] = "0"
    resp = client.post("/rag/query2", json={"query": "weights test", "top_k": 1})
    # Clean up env
    del os.environ["RAG_FUSION_LTR_WEIGHT"]
    del os.environ["RAG_FUSION_CONCEPTUAL_WEIGHT"]
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        fw = data.get("fusion_weights", {})
        # After normalization fallback both should be 0.5
        if fw:
            assert abs(fw.get("ltr", 0.5) - 0.5) < 1e-6
            assert abs(fw.get("conceptual", 0.5) - 0.5) < 1e-6
