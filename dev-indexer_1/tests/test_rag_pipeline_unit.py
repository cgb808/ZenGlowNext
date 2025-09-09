"""Unit tests for RAGPipeline using mocks."""

from typing import Any, Dict, List, Optional

from app.rag.pipeline import RAGPipeline


class FakeDB:
    def __init__(self, rows: Optional[List[Dict[str, Any]]] = None):
        self.rows: List[Dict[str, Any]] = rows or [{"text": "Doc A"}, {"text": "Doc B"}]

    def vector_search(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        return self.rows[:top_k]


class FakeEmbedder:
    def embed(self, text: str) -> List[float]:
        return [0.1, 0.2, 0.3]


class FakeLLM:
    def generate(self, prompt: str) -> str:
        return "LLM: " + prompt.split("Question:")[-1].strip()


def test_rag_pipeline_basic() -> None:
    pipeline = RAGPipeline(db_client=FakeDB(), embedder=FakeEmbedder(), llm_client=FakeLLM())
    out = pipeline.run("What is up?", top_k=2)
    assert "What is up?" in out
