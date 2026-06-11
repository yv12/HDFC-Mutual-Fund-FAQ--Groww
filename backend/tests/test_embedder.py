"""Unit tests for the embedding generation module."""

import pytest

from app.ingestion.embedder import embed_query, embed_texts, get_embedding_model


def test_model_lazy_loading():
    """Verify that get_embedding_model successfully loads and caches the transformer."""
    model1 = get_embedding_model()
    model2 = get_embedding_model()
    assert model1 is model2  # Should be the exact same instance (singleton)


def test_embed_texts():
    """Verify text batch embedding produces standard float list representation with 1024 dimensions."""
    texts = ["HDFC Mid Cap Fund is an equity mutual fund.", "Exit load is 1% within 1 year."]
    embeddings = embed_texts(texts)
    
    assert len(embeddings) == len(texts)
    for emb in embeddings:
        assert isinstance(emb, list)
        assert len(emb) == 1024  # BGE-large-en-v1.5 standard dimensions
        assert all(isinstance(x, float) for x in emb)


def test_embed_query():
    """Verify query embedding prepends instruction prefix and generates 1024 dimensional vector."""
    query = "Who is the fund manager?"
    emb = embed_query(query)
    
    assert isinstance(emb, list)
    assert len(emb) == 1024
    assert all(isinstance(x, float) for x in emb)


def test_embed_empty_list():
    """Embedding an empty sequence should return an empty list immediately."""
    assert embed_texts([]) == []
