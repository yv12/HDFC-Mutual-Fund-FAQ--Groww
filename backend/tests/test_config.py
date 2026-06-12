"""Tests for the configuration module."""

from app.config import settings


def test_settings_defaults():
    """Settings should load with sensible defaults even without a .env file."""
    assert settings.llm_model == "grok-3-mini"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.embedding_dimensions == 384
    assert settings.embedding_device == "cpu"
    assert settings.xai_base_url == "https://api.x.ai/v1"
    assert settings.chroma_collection_name == "mutual_fund_faq"
    assert settings.retrieval_top_k == 4
    assert settings.similarity_threshold == 0.5
    assert settings.chunk_size == 250
    assert settings.chunk_overlap == 30
    assert settings.api_port == 8000
    assert settings.rate_limit_per_minute == 20


def test_cors_origin_list():
    """CORS origins string should be parsed into a list."""
    origins = settings.cors_origin_list
    assert isinstance(origins, list)
    assert len(origins) >= 1
