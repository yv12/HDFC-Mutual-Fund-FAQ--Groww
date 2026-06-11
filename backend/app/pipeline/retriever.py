"""
Retriever module — handles semantic search and metadata filtering in ChromaDB.

Pre-inspects user queries to apply target scheme routing filters, mitigating
cross-fund similarity matches (e.g. returning Small Cap NAV for a Mid Cap query).
Filters results using the similarity threshold.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.config import settings
from app.ingestion.vector_store import query_similar

logger = logging.getLogger(__name__)

# Route query keywords to exact database scheme names.
SCHEME_ROUTING_MAP = {
    # Mid Cap Fund — official short names
    "mid cap": "HDFC Mid Cap Fund Direct Growth",
    "mid-cap": "HDFC Mid Cap Fund Direct Growth",
    "midcap": "HDFC Mid Cap Fund Direct Growth",

    # Large Cap Fund — official short names
    "large cap": "HDFC Large Cap Fund Direct Growth",
    "large-cap": "HDFC Large Cap Fund Direct Growth",
    "largecap": "HDFC Large Cap Fund Direct Growth",

    # Small Cap Fund
    "small cap": "HDFC Small Cap Fund Direct Growth",
    "small-cap": "HDFC Small Cap Fund Direct Growth",
    "smallcap": "HDFC Small Cap Fund Direct Growth",

    # Gold ETF Fund
    "gold": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "gold etf": "HDFC Gold ETF Fund of Fund Direct Plan Growth",

    # Defence Fund
    "defence": "HDFC Defence Fund Direct Growth",
    "defense": "HDFC Defence Fund Direct Growth",
}


def retrieve_relevant_context(
    query: str,
    limit: int | None = None,
    threshold: float | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve semantically relevant chunks for a user query.
    Applies scheme routing filters if a scheme keyword is detected in the query.
    Filters results using similarity threshold.
    """
    _limit = limit or settings.retrieval_top_k
    _threshold = threshold or settings.similarity_threshold

    s = query.lower()
    
    # 1. Detect target scheme
    matched_scheme = None
    matched_keywords = []
    
    for kw, scheme_name in SCHEME_ROUTING_MAP.items():
        # Match word boundaries for keyword safety (e.g. avoid matching "gold" in unrelated words)
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, s):
            if scheme_name not in matched_keywords:
                matched_keywords.append(scheme_name)
                
    # If exactly one unique scheme is matched, apply metadata filter routing
    if len(matched_keywords) == 1:
        matched_scheme = matched_keywords[0]
        logger.info("Retriever routed query exclusively to scheme: %s", matched_scheme)

    # 2. Build ChromaDB metadata filter
    where_filter = None
    if matched_scheme:
        where_filter = {"scheme_name": matched_scheme}

    # 3. Query vector store
    raw_results = query_similar(query, limit=_limit, where_filter=where_filter)

    # 4. Filter by similarity threshold
    filtered_results = []
    for r in raw_results:
        sim = r.get("similarity", 0.0)
        if sim >= _threshold:
            filtered_results.append(r)
            logger.debug("Kept chunk %s with similarity: %.4f", r["chunk_id"], sim)
        else:
            logger.debug("Dropped chunk %s below similarity: %.4f (threshold=%.2f)", r["chunk_id"], sim, _threshold)

    logger.info(
        "Retrieved %d / %d chunks above similarity threshold %.2f",
        len(filtered_results), len(raw_results), _threshold
    )
    return filtered_results
