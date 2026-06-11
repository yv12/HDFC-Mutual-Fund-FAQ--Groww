"""
Vector store module — persistent ChromaDB indexing and querying.

Handles storing vector embeddings along with source text and metadata, and
performing semantic queries with optional metadata routing filters.
"""

from __future__ import annotations

import logging
from typing import Any

import chromadb

from app.config import settings
from app.ingestion.chunker import Chunk
from app.ingestion.embedder import embed_query, embed_texts

logger = logging.getLogger(__name__)

# Lazy singleton clients
_chroma_client: chromadb.PersistentClient | None = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Lazy-load and return the persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        logger.info("Initializing ChromaDB persistent client at %s", settings.chroma_persist_dir)
        try:
            _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        except Exception as exc:
            logger.error("Failed to initialize ChromaDB client: %s", exc)
            raise exc
    return _chroma_client


def get_collection() -> chromadb.Collection:
    """Get or create the mutual fund FAQ collection with Cosine similarity distance."""
    client = get_chroma_client()
    # Configure Cosine distance metric for the HNSW index space
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(chunks: list[Chunk]) -> None:
    """
    Generate vector embeddings for all chunks and index them in ChromaDB.
    This operation is idempotent (overwrite or ignore duplicate IDs).
    """
    if not chunks:
        return

    collection = get_collection()

    ids = [c.chunk_id for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [c.to_dict() for c in chunks]

    logger.info("Generating embeddings for %d chunks...", len(chunks))
    embeddings = embed_texts(documents)

    logger.info("Storing %d chunks in collection '%s' ...", len(chunks), settings.chroma_collection_name)
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )
    logger.info("✓ Vector store indexing complete.")


def query_similar(
    query: str,
    limit: int | None = None,
    where_filter: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Perform a vector similarity search in ChromaDB.
    
    Args:
        query: The raw user search query string.
        limit: Number of top-k results to return. Defaults to settings.retrieval_top_k.
        where_filter: ChromaDB metadata filter dictionary (e.g. {"scheme_name": "..."}).

    Returns:
        List of results containing chunk_id, text, metadata dict, and similarity score.
    """
    _limit = limit or settings.retrieval_top_k
    collection = get_collection()

    # Generate query embedding with query instruction prefix
    query_vector = embed_query(query)

    logger.debug("Querying vector store (limit=%d, filter=%s)", _limit, where_filter)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=_limit,
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
            # Thus, similarity = 1.0 - distance
            dist = distances[i] if i < len(distances) else 0.0
            similarity = 1.0 - dist

            formatted_results.append({
                "chunk_id": ids[i],
                "text": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "similarity": similarity,
            })

    return formatted_results


def reset_store() -> None:
    """Reset the database collection (deletes all indexed records)."""
    client = get_chroma_client()
    try:
        client.delete_collection(settings.chroma_collection_name)
        logger.info("ChromaDB collection '%s' deleted.", settings.chroma_collection_name)
    except Exception as exc:
        logger.warning("Could not reset ChromaDB collection (it may not exist): %s", exc)
