"""
Unit tests for the citation validator module.
"""

from app.pipeline.citation_validator import validate_citations
from app.api.schemas import CitationInfo


def test_validate_citations_valid_url():
    """Verify that a valid URL from chunk metadata is preserved."""
    chunks = [
        {
            "chunk_id": "hdfc-mid-cap-001",
            "text": "HDFC Mid Cap Fund details...",
            "metadata": {
                "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                "scheme_name": "HDFC Mid Cap Fund – Direct Growth",
                "section": "Overview",
                "scraped_at": "2026-06-02T10:00:00Z",
            },
        }
    ]
    response = "You can read more at https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth."
    cleaned, citation, footer = validate_citations(response, chunks)

    assert citation.source_url == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    assert citation.scheme_name == "HDFC Mid Cap Fund – Direct Growth"
    assert citation.section == "Overview"
    assert "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth" in cleaned
    assert "Last updated from sources: 2026-06-02" == footer


def test_validate_citations_hallucinated_url():
    """Verify that a hallucinated URL is replaced with a text citation fallback."""
    chunks = [
        {
            "chunk_id": "hdfc-mid-cap-001",
            "text": "HDFC Mid Cap Fund details...",
            "metadata": {
                "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                "scheme_name": "HDFC Mid Cap Fund – Direct Growth",
                "section": "Fund Details",
                "scraped_at": "2026-06-02T10:00:00Z",
            },
        }
    ]
    response = "The expense ratio is 0.74%. See https://groww.in/invalid-url for more."
    cleaned, citation, footer = validate_citations(response, chunks)

    # Hallucinated URL should be stripped/replaced
    assert "https://groww.in/invalid-url" not in cleaned
    assert "[HDFC Mid Cap Fund – Direct Growth - Fund Details]" in cleaned
    # Citation should fallback to top chunk metadata
    assert citation.source_url == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    assert citation.scheme_name == "HDFC Mid Cap Fund – Direct Growth"
    assert citation.section == "Fund Details"
    assert "Last updated from sources: 2026-06-02" == footer


def test_validate_citations_no_url():
    """Verify that if no URL is in response, top chunk URL is attached as metadata."""
    chunks = [
        {
            "chunk_id": "hdfc-large-cap-002",
            "text": "HDFC Large Cap Fund details...",
            "metadata": {
                "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
                "scheme_name": "HDFC Large Cap Fund – Direct Growth",
                "section": "Fund Details",
                "scraped_at": "2026-06-02T12:00:00Z",
            },
        }
    ]
    response = "The NAV of the Large Cap Fund is 150.25."
    cleaned, citation, footer = validate_citations(response, chunks)

    assert cleaned == response
    assert citation.source_url == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert citation.scheme_name == "HDFC Large Cap Fund – Direct Growth"
    assert citation.section == "Fund Details"
    assert "Last updated from sources: 2026-06-02" == footer


def test_validate_citations_empty_chunks():
    """Verify handling when chunks are empty."""
    response = "The answer is here."
    cleaned, citation, footer = validate_citations(response, [])

    assert cleaned == response
    assert citation.source_url is None
    assert citation.scheme_name is None
    assert citation.section is None
    assert footer == "Last updated from sources: unknown"
