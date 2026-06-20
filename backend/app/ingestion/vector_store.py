"""
Vector store module — dual-mode: local ChromaDB or Qdrant Cloud.

Supports two providers controlled by the VECTOR_DB_PROVIDER setting:
  - "chroma": Local persistent ChromaDB (543 MB on disk, high RAM).
  - "qdrant": Qdrant Cloud free tier (remote, zero local storage).

Both modes expose the same public API:
  get_collection(), add_chunks(), query_similar(), reset_store()
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.ingestion.chunker import Chunk
from app.ingestion.embedder import embed_query, embed_texts

logger = logging.getLogger(__name__)


# =====================================================================
# ChromaDB provider (local)
# =====================================================================

_chroma_client = None


def _get_chroma_client():
    """Lazy-load the persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        logger.info("Initializing ChromaDB persistent client at %s", settings.chroma_persist_dir)
        try:
            _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        except Exception as exc:
            logger.error("Failed to initialize ChromaDB client: %s", exc)
            raise exc
    return _chroma_client


def _get_chroma_collection():
    """Get or create the ChromaDB collection with Cosine similarity."""
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _add_chunks_chroma(chunks: list[Chunk]) -> None:
    """Index chunks in local ChromaDB."""
    collection = _get_chroma_collection()
    ids = [c.chunk_id for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [c.to_dict() for c in chunks]

    logger.info("Generating embeddings for %d chunks...", len(chunks))
    embeddings = embed_texts(documents)

    logger.info("Storing %d chunks in ChromaDB collection '%s' ...", len(chunks), settings.chroma_collection_name)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )
    logger.info("✓ ChromaDB indexing complete.")


def _query_similar_chroma(query: str, limit: int, where_filter: dict | None) -> list[dict[str, Any]]:
    """Perform vector similarity search in local ChromaDB."""
    collection = _get_chroma_collection()
    query_vector = embed_query(query)

    logger.debug("Querying ChromaDB (limit=%d, filter=%s)", limit, where_filter)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=limit,
        where=where_filter,
    )

    formatted_results = []
    if results and results.get("ids") and len(results["ids"]) > 0:
        ids = results["ids"][0]
        documents = results["documents"][0] if results.get("documents") else []
        metadatas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i in range(len(ids)):
            # Cosine distance in Chroma: distance = 1.0 - cosine_similarity
            dist = distances[i] if i < len(distances) else 0.0
            similarity = 1.0 - dist
            formatted_results.append({
                "chunk_id": ids[i],
                "text": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "similarity": similarity,
            })

    return formatted_results


def _reset_store_chroma() -> None:
    """Delete the ChromaDB collection."""
    client = _get_chroma_client()
    try:
        client.delete_collection(settings.chroma_collection_name)
        logger.info("ChromaDB collection '%s' deleted.", settings.chroma_collection_name)
    except Exception as exc:
        logger.warning("Could not reset ChromaDB collection (it may not exist): %s", exc)


# =====================================================================
# Qdrant Cloud provider
# =====================================================================

_qdrant_client = None


def _get_qdrant_client():
    """Lazy-initialize the Qdrant Cloud client."""
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        url = settings.qdrant_url
        api_key = settings.qdrant_api_key
        if not url:
            raise ValueError(
                "QDRANT_URL is required when VECTOR_DB_PROVIDER='qdrant'. "
                "Create a free cluster at https://cloud.qdrant.io"
            )
        _qdrant_client = QdrantClient(url=url, api_key=api_key or None)
        logger.info("Qdrant Cloud client connected to %s", url)
    return _qdrant_client


def _ensure_qdrant_collection() -> None:
    """Create the Qdrant collection if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams
    client = _get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    # Check if collection exists
    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name not in existing_names:
        logger.info("Creating Qdrant collection '%s' (dim=%d, cosine) ...", collection_name, settings.embedding_dimensions)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )
        logger.info("✓ Qdrant collection created.")
    else:
        logger.info("Qdrant collection '%s' already exists.", collection_name)


def _add_chunks_qdrant(chunks: list[Chunk]) -> None:
    """Index chunks in Qdrant Cloud."""
    from qdrant_client.models import PointStruct
    client = _get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    _ensure_qdrant_collection()

    ids_list = [c.chunk_id for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [c.to_dict() for c in chunks]

    logger.info("Generating embeddings for %d chunks...", len(chunks))
    embeddings = embed_texts(documents)

    # Build Qdrant points — use hash of chunk_id for numeric ID
    points = []
    for i, chunk in enumerate(chunks):
        payload = metadatas[i].copy()
        payload["text"] = documents[i]
        payload["chunk_id"] = ids_list[i]
        # Qdrant needs integer or UUID point IDs — use a deterministic hash
        point_id = abs(hash(ids_list[i])) % (2**63)
        points.append(PointStruct(
            id=point_id,
            vector=embeddings[i],
            payload=payload,
        ))

    logger.info("Upserting %d points to Qdrant collection '%s' ...", len(points), collection_name)
    # Upsert in batches of 100
    batch_size = 100
    for start in range(0, len(points), batch_size):
        batch = points[start:start + batch_size]
        client.upsert(collection_name=collection_name, points=batch)

    logger.info("✓ Qdrant indexing complete.")


def _query_similar_qdrant(query: str, limit: int, where_filter: dict | None) -> list[dict[str, Any]]:
    """Perform vector similarity search in Qdrant Cloud."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    client = _get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    query_vector = embed_query(query)

    # Build Qdrant filter from the simple where_filter dict
    qdrant_filter = None
    if where_filter:
        conditions = []
        for key, value in where_filter.items():
            conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        qdrant_filter = Filter(must=conditions)

    logger.debug("Querying Qdrant (limit=%d, filter=%s)", limit, where_filter)
    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )

    formatted_results = []
    for point in results.points:
        payload = point.payload or {}
        formatted_results.append({
            "chunk_id": payload.get("chunk_id", str(point.id)),
            "text": payload.get("text", ""),
            "metadata": {k: v for k, v in payload.items() if k not in ("text",)},
            "similarity": point.score,  # Qdrant returns cosine similarity directly
        })

    return formatted_results


def _reset_store_qdrant() -> None:
    """Delete the Qdrant collection."""
    client = _get_qdrant_client()
    try:
        client.delete_collection(settings.qdrant_collection_name)
        logger.info("Qdrant collection '%s' deleted.", settings.qdrant_collection_name)
    except Exception as exc:
        logger.warning("Could not reset Qdrant collection: %s", exc)


# =====================================================================
# Public API (provider-agnostic — same interface as before)
# =====================================================================

def get_collection():
    """Get or create the vector store collection (provider-agnostic)."""
    if settings.vector_db_provider == "qdrant":
        _ensure_qdrant_collection()
        return _get_qdrant_client()
    return _get_chroma_collection()


def add_chunks(chunks: list[Chunk]) -> None:
    """
    Generate vector embeddings for all chunks and index them.
    This operation is idempotent (upsert/overwrite duplicate IDs).
    """
    if not chunks:
        return

    if settings.vector_db_provider == "qdrant":
        _add_chunks_qdrant(chunks)
    else:
        _add_chunks_chroma(chunks)


def query_similar(
    query: str,
    limit: int | None = None,
    where_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Perform a vector similarity search.

    Args:
        query: The raw user search query string.
        limit: Number of top-k results to return. Defaults to settings.retrieval_top_k.
        where_filter: Metadata filter dictionary (e.g. {"scheme_name": "..."}).

    Returns:
        List of results containing chunk_id, text, metadata dict, and similarity score.
    """
    _limit = limit or settings.retrieval_top_k

    if settings.vector_db_provider == "qdrant":
        return _query_similar_qdrant(query, _limit, where_filter)
    return _query_similar_chroma(query, _limit, where_filter)


def reset_store() -> None:
    """Reset the vector store collection (deletes all indexed records)."""
    if settings.vector_db_provider == "qdrant":
        _reset_store_qdrant()
    else:
        _reset_store_chroma()
