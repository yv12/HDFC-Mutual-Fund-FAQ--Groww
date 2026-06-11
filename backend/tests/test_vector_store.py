"""Unit tests for the ChromaDB vector store module."""

import pytest

from app.ingestion.chunker import Chunk
from app.ingestion.vector_store import add_chunks, query_similar, reset_store


@pytest.fixture(autouse=True)
def run_around_tests():
    """Wipe collection before and after every test to run in isolation."""
    reset_store()
    yield
    reset_store()


def test_add_and_query_chunks():
    """Verify that chunks can be indexed and queried semantically with metadata filtering."""
    chunks = [
        Chunk(
            chunk_id="test-midcap-001",
            text="HDFC Mid Cap Fund Direct Growth has an expense ratio of 0.73%.",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            scheme_name="HDFC Mid Cap Fund – Direct Growth",
            section="Fund Details",
            scraped_at="2026-06-03T12:00:00Z",
        ),
        Chunk(
            chunk_id="test-largecap-001",
            text="HDFC Large Cap Fund Direct Growth exit load is 1% if redeemed within 1 year.",
            source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            scheme_name="HDFC Large Cap Fund – Direct Growth",
            section="Exit Load",
            scraped_at="2026-06-03T12:00:00Z",
        ),
    ]

    # Index chunks
    add_chunks(chunks)

    # 1. Global semantic query
    results = query_similar("What is the expense ratio?", limit=2)
    assert len(results) >= 1
    # The midcap chunk should rank highest for expense ratio query
    assert results[0]["chunk_id"] == "test-midcap-001"
    assert "0.73%" in results[0]["text"]
    assert isinstance(results[0]["similarity"], float)

    # 2. Query with specific scheme metadata filter (prevents cross-contamination)
    # Asking for "exit load" but restricting search to "Mid Cap"
    results_filtered = query_similar(
        query="What is the exit load?",
        limit=2,
        where_filter={"scheme_name": "HDFC Mid Cap Fund – Direct Growth"},
    )
    # The Large Cap exit load chunk matches query text but should be blocked by the filter
    assert len(results_filtered) >= 1
    for r in results_filtered:
        assert r["metadata"]["scheme_name"] == "HDFC Mid Cap Fund – Direct Growth"
        assert r["chunk_id"] != "test-largecap-001"
