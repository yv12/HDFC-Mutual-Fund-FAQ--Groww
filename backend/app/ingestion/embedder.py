"""
Embedding generation module — dual-mode: local or HuggingFace Inference API.

Supports two providers controlled by the EMBEDDING_PROVIDER setting:
  - "local": Uses sentence-transformers SentenceTransformer (high RAM, zero API cost).
  - "api":   Uses HuggingFace Serverless Inference API (low RAM, rate-limited).

Both modes produce identical embeddings from BAAI/bge-large-en-v1.5.
"""

from __future__ import annotations

import logging
import time
from typing import Sequence

from app.config import settings

logger = logging.getLogger(__name__)

# ── BGE query instruction prefix ─────────────────────────────────
# BGE-large-en-v1.5 requires this prefix for queries (asymmetric search).
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

# ── Lazy singleton instances ─────────────────────────────────────
_local_model_instance = None
_hf_client_instance = None


# =====================================================================
# Local provider (sentence-transformers)
# =====================================================================

def _get_local_model():
    """Lazy-load the local SentenceTransformer model."""
    global _local_model_instance
    if _local_model_instance is None:
        from sentence_transformers import SentenceTransformer
        logger.info(
            "Loading local embedding model '%s' on device '%s' ...",
            settings.embedding_model,
            settings.embedding_device,
        )
        try:
            _local_model_instance = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device,
            )
            logger.info("Local embedding model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load local embedding model: %s", exc)
            raise exc
    return _local_model_instance


def _embed_texts_local(texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings locally via sentence-transformers."""
    model = _get_local_model()
    embeddings = model.encode(list(texts), convert_to_numpy=False, show_progress_bar=False)
    return [[float(val) for val in emb] for emb in embeddings]


def _embed_query_local(query: str) -> list[float]:
    """Generate a single query embedding locally via sentence-transformers."""
    full_query = f"{_BGE_QUERY_PREFIX}{query}"
    model = _get_local_model()
    embedding = model.encode(full_query, convert_to_numpy=False, show_progress_bar=False)
    return [float(val) for val in embedding]


# =====================================================================
# API provider (HuggingFace Inference API)
# =====================================================================

def _get_hf_client():
    """Lazy-initialize the HuggingFace InferenceClient."""
    global _hf_client_instance
    if _hf_client_instance is None:
        from huggingface_hub import InferenceClient
        token = settings.hf_api_token
        if not token:
            raise ValueError(
                "HF_API_TOKEN is required when EMBEDDING_PROVIDER='api'. "
                "Get a free token at https://huggingface.co/settings/tokens"
            )
        _hf_client_instance = InferenceClient(token=token)
        logger.info("HuggingFace InferenceClient initialized for model '%s'.", settings.embedding_model)
    return _hf_client_instance


def _hf_feature_extraction(text: str, max_retries: int = 3) -> list[float]:
    """Call HF Inference API with retry logic for rate limits."""
    client = _get_hf_client()
    for attempt in range(1, max_retries + 1):
        try:
            result = client.feature_extraction(
                text,
                model=settings.embedding_model,
            )
            # Result can be a nested list; flatten to 1D
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], list):
                    # Model returned [batch][tokens][dims] — take mean pooling
                    # or it's already [1][dims]
                    import numpy as np
                    arr = np.array(result)
                    if arr.ndim == 3:
                        # Shape: (1, seq_len, dims) → mean over seq_len
                        return arr.mean(axis=1)[0].tolist()
                    elif arr.ndim == 2:
                        return arr[0].tolist()
                return [float(v) for v in result]
            return [float(v) for v in result]
        except Exception as exc:
            error_str = str(exc).lower()
            if "429" in error_str or "rate" in error_str or "too many" in error_str:
                wait = 2 ** attempt
                logger.warning(
                    "HF API rate limit hit (attempt %d/%d). Retrying in %ds ...",
                    attempt, max_retries, wait,
                )
                time.sleep(wait)
            else:
                logger.error("HF Inference API error: %s", exc)
                raise
    raise RuntimeError(f"HF Inference API failed after {max_retries} retries")


def _embed_texts_api(texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings via HuggingFace Inference API (batch)."""
    results = []
    for text in texts:
        results.append(_hf_feature_extraction(text))
    return results


def _embed_query_api(query: str) -> list[float]:
    """Generate a single query embedding via HuggingFace Inference API."""
    full_query = f"{_BGE_QUERY_PREFIX}{query}"
    return _hf_feature_extraction(full_query)


# =====================================================================
# Cloudflare Workers AI provider (@cf/baai/bge-large-en-v1.5)
# =====================================================================

def _cf_feature_extraction(texts: str | Sequence[str], max_retries: int = 3) -> list[float] | list[list[float]]:
    """Call Cloudflare Workers AI with retry logic for @cf/baai/bge-large-en-v1.5 embeddings."""
    import requests

    account_id = settings.cloudflare_account_id
    token = settings.cloudflare_api_token
    if not account_id or not token:
        raise ValueError(
            "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required when EMBEDDING_PROVIDER='cloudflare'."
        )

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/baai/bge-large-en-v1.5"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    is_single = isinstance(texts, str)
    payload = {"text": [texts] if is_single else list(texts)}

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning("Cloudflare Workers AI rate limit hit. Retrying in %ds...", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise RuntimeError(f"Cloudflare Workers AI error: {data.get('errors')}")
            result_data = data.get("result", {}).get("data", [])
            if is_single:
                return [float(v) for v in result_data[0]]
            return [[float(v) for v in vec] for vec in result_data]
        except Exception as exc:
            if attempt == max_retries:
                logger.error("Cloudflare Workers AI error: %s", exc)
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Cloudflare Workers AI failed after {max_retries} retries")


def _embed_texts_cloudflare(texts: Sequence[str]) -> list[list[float]]:
    """Generate embeddings via Cloudflare Workers AI (batch)."""
    results = []
    batch_size = 25
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        results.extend(_cf_feature_extraction(batch))
    return results


def _embed_query_cloudflare(query: str) -> list[float]:
    """Generate a single query embedding via Cloudflare Workers AI."""
    full_query = f"{_BGE_QUERY_PREFIX}{query}"
    return _cf_feature_extraction(full_query)


# =====================================================================
# Public API (provider-agnostic)
# =====================================================================

def get_embedding_model():
    """Return the model instance (local) or client (API) — for backward compatibility."""
    provider = settings.embedding_provider.lower()
    if provider == "cloudflare":
        return "cloudflare"
    elif provider == "api":
        return _get_hf_client()
    return _get_local_model()


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """
    Generate embeddings for a sequence of text chunks (passages).
    Used during offline corpus ingestion. No query prefix is prepended.
    """
    if not texts:
        return []

    provider = settings.embedding_provider.lower()
    if provider == "cloudflare":
        logger.info("Embedding %d texts via Cloudflare Workers AI ...", len(texts))
        return _embed_texts_cloudflare(texts)
    elif provider == "api":
        logger.info("Embedding %d texts via HuggingFace Inference API ...", len(texts))
        return _embed_texts_api(texts)
    else:
        logger.info("Embedding %d texts locally via sentence-transformers ...", len(texts))
        return _embed_texts_local(texts)


def embed_query(query: str) -> list[float]:
    """
    Generate embedding for a single search query.
    Prepends the required asymmetric search instruction prefix for BGE models.
    """
    provider = settings.embedding_provider.lower()
    if provider == "cloudflare":
        return _embed_query_cloudflare(query)
    elif provider == "api":
        return _embed_query_api(query)
    else:
        return _embed_query_local(query)
