"""
Citation validator module — enforces zero-hallucination URL policy.

Implementation in Phase 4:
  - Parse LLM response for URLs
  - Verify each URL exists verbatim in chunk metadata
  - Strip hallucinated URLs → replace with text-only citation
  - Attach source_url from top-ranked chunk if none present
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.api.schemas import CitationInfo

logger = logging.getLogger(__name__)


def validate_citations(
    llm_response: str,
    chunks: list[dict[str, Any]],
) -> tuple[str, CitationInfo, str]:
    """
    Validate all URLs in LLM response against retrieved chunks.

    Returns:
        tuple of (cleaned_answer, CitationInfo, footer_string)
    """
    if not chunks:
        logger.warning("No chunks provided for citation validation.")
        return (
            llm_response,
            CitationInfo(source_url=None, scheme_name=None, section=None),
            "Last updated from sources: unknown",
        )

    top_chunk = chunks[0]
    top_meta = top_chunk.get("metadata", {})

    def find_matching_chunk(url: str) -> dict[str, Any] | None:
        """Find a chunk whose source_url matches the given URL verbatim."""
        for c in chunks:
            meta = c.get("metadata", {})
            if meta.get("source_url") == url:
                return c
        return None

    # Regex to capture http/https URLs.
    # Captures non-whitespace sequences starting with http:// or https://.
    raw_urls = re.findall(r"(https?://\S+)", llm_response)

    cleaned_answer = llm_response
    matched_chunk = None
    processed_urls = set()

    for raw_url in raw_urls:
        # Clean trailing punctuation commonly found at the end of sentences/parentheses
        cleaned_url = raw_url.rstrip(".,;!?'\")")
        if cleaned_url.endswith(")"):
            if "(" not in cleaned_url:
                cleaned_url = cleaned_url[:-1]

        if cleaned_url in processed_urls:
            continue
        processed_urls.add(cleaned_url)

        chunk = find_matching_chunk(cleaned_url)
        if chunk:
            logger.info("Verbatim URL verified: %s", cleaned_url)
            if not matched_chunk:
                matched_chunk = chunk
        else:
            logger.warning("Hallucinated URL detected and stripped: %s", cleaned_url)
            scheme = top_meta.get("scheme_name", "HDFC Mutual Fund")
            section = top_meta.get("section", "General")
            replacement = f"[{scheme} - {section}]"
            # Replace only the cleaned_url so surrounding punctuation is preserved
            cleaned_answer = cleaned_answer.replace(cleaned_url, replacement)

    # Determine citation details
    if matched_chunk:
        meta = matched_chunk.get("metadata", {})
        citation = CitationInfo(
            source_url=meta.get("source_url"),
            scheme_name=meta.get("scheme_name"),
            section=meta.get("section"),
        )
        scraped_at = meta.get("scraped_at", "unknown")
    else:
        # Fallback to top-ranked chunk
        citation = CitationInfo(
            source_url=top_meta.get("source_url"),
            scheme_name=top_meta.get("scheme_name"),
            section=top_meta.get("section"),
        )
        scraped_at = top_meta.get("scraped_at", "unknown")

    # Format footer
    # If scraped_at is an ISO format string, we can try to extract just the date part (YYYY-MM-DD)
    # for cleaner representation, or keep it as-is. Standardizing:
    date_str = scraped_at.split("T")[0] if scraped_at and "T" in scraped_at else scraped_at
    footer = f"Last updated from sources: {date_str}"

    return cleaned_answer, citation, footer
