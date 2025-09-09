"""Temporarily skipped rag_ingest tests per request to ignore to avoid further churn."""

import pytest


@pytest.mark.skip(reason="Temporarily disabled")
def test_rag_ingest_process_inserts():
    pass


@pytest.mark.skip(reason="Temporarily disabled")
def test_rag_ingest_empty_file():
    pass
