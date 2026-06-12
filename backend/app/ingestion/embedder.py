"""
Embedding generation module — local BGE-small-en-v1.5 via sentence-transformers.

Provides functions to generate vector embeddings for text chunks (indexing)
and user queries (retrieval). Runs entirely locally with zero API costs.
"""

from __future__ import annotations

import logging
from typing import Sequence

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy singleton model instance
_model_instance: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy-load and return the SentenceTransformer model instance."""
    global _model_instance
    if _model_instance is None:
        logger.info(
            "Loading embedding model '%s' on device '%s' ...",
            settings.embedding_model,
            settings.embedding_device,
        )
        try:
            _model_instance = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device,
            )
            logger.info("Embedding model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            raise exc
    return _model_instance


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """
    Generate embeddings for a sequence of text chunks (passages).
    Used during offline corpus ingestion. No query prefix is prepended.
    """
    if not texts:
        return []
    
    model = get_embedding_model()
    # convert_to_numpy=False returns native Python lists
    embeddings = model.encode(list(texts), convert_to_numpy=False, show_progress_bar=False)
    
    # Cast elements explicitly to standard float for serialization safety
    return [[float(val) for val in emb] for emb in embeddings]


def embed_query(query: str) -> list[float]:
    """
    Generate embedding for a single search query.
    Prepends the required asymmetric search instruction prefix for BGE models.
    """
    # BGE v1.5 models require this prefix for queries to search effectively
    prefix = "Represent this sentence for searching relevant passages: "
    full_query = f"{prefix}{query}"
    
    model = get_embedding_model()
    embedding = model.encode(full_query, convert_to_numpy=False, show_progress_bar=False)
    
    return [float(val) for val in embedding]
