"""
Unit tests for the document chunking module.

Tests cover:
  - Section building from ScrapedFund data
  - Text splitting with overlap
  - Chunk metadata correctness
  - Deterministic chunk IDs (idempotency)
  - Token-count bounds
"""

import pytest
from app.scraper.scraper import ScrapedFund, FundManager
from app.ingestion.chunker import (
    Chunk,
    chunk_fund,
    chunk_all_funds,
    _approx_token_count,
    _build_sections,
    _slugify,
    _split_text,
    _make_chunk_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_fund() -> ScrapedFund:
    """A fully-populated ScrapedFund for testing."""
    return ScrapedFund(
        scheme_name="HDFC Mid Cap Fund – Direct Growth",
        source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        scraped_at="2026-06-03T12:00:00Z",
        category="Equity",
        sub_category="Mid Cap",
        risk_level="Very High Risk",
        nav="₹219.67",
        nav_date="02 Jun '26",
        min_sip="₹100",
        min_lumpsum="₹5,000",
        aum="₹94,744.72 Cr",
        expense_ratio="0.73%",
        rating="5",
        exit_load="1% if redeemed within 1 year",
        lock_in_period="",
        stamp_duty="0.005%",
        benchmark="NIFTY Midcap 150 - TRI",
        fund_house="HDFC Mutual Fund",
        launch_date="01 Jan 2013",
        fund_managers=[
            FundManager(name="Chirag Setalvad", since="Jun 2014"),
        ],
        about="HDFC Mid Cap Fund is an open ended mid cap equity scheme.",
        investment_objective="To generate long-term capital appreciation.",
        returns_1y="+1.29%",
        returns_3y="+22.05%",
        returns_5y="+28.50%",
    )


@pytest.fixture
def minimal_fund() -> ScrapedFund:
    """A ScrapedFund with minimal data (only required fields)."""
    return ScrapedFund(
        scheme_name="Test Fund",
        source_url="https://example.com",
        scraped_at="2026-01-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestApproxTokenCount:
    def test_empty(self):
        assert _approx_token_count("") == 0

    def test_single_word(self):
        assert _approx_token_count("hello") == 1

    def test_sentence(self):
        assert _approx_token_count("The quick brown fox jumps") == 5


class TestSlugify:
    def test_basic(self):
        assert _slugify("HDFC Mid Cap Fund – Direct Growth") == "hdfc-mid-cap-fund-direct"

    def test_special_chars(self):
        slug = _slugify("HDFC Gold ETF Fund of Fund – Direct Growth")
        assert slug.startswith("hdfc-gold-etf-fund-of")


class TestMakeChunkId:
    def test_deterministic(self):
        id1 = _make_chunk_id("hdfc-mid", "Overview", 0)
        id2 = _make_chunk_id("hdfc-mid", "Overview", 0)
        assert id1 == id2

    def test_different_index(self):
        id1 = _make_chunk_id("hdfc-mid", "Overview", 0)
        id2 = _make_chunk_id("hdfc-mid", "Overview", 1)
        assert id1 != id2

    def test_format(self):
        cid = _make_chunk_id("hdfc-mid", "Fund Details", 2)
        assert cid.startswith("hdfc-mid-")
        assert cid.endswith("-002")


# ---------------------------------------------------------------------------
# Section building
# ---------------------------------------------------------------------------

class TestBuildSections:
    def test_sample_fund_has_sections(self, sample_fund: ScrapedFund):
        sections = _build_sections(sample_fund)
        section_names = [s[0] for s in sections]
        assert "Overview" in section_names
        assert "Fund Details" in section_names
        assert "Exit Load" in section_names
        assert "Fund Managers" in section_names
        assert "Returns" in section_names
        assert "About" in section_names

    def test_minimal_fund_has_overview(self, minimal_fund: ScrapedFund):
        sections = _build_sections(minimal_fund)
        section_names = [s[0] for s in sections]
        assert "Overview" in section_names

    def test_overview_contains_scheme_name(self, sample_fund: ScrapedFund):
        sections = _build_sections(sample_fund)
        overview = next(text for name, text in sections if name == "Overview")
        assert "HDFC Mid Cap Fund" in overview

    def test_fund_details_contains_key_stats(self, sample_fund: ScrapedFund):
        sections = _build_sections(sample_fund)
        details = next(text for name, text in sections if name == "Fund Details")
        assert "₹219.67" in details
        assert "0.73%" in details
        assert "₹100" in details


# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------

class TestSplitText:
    def test_short_text_not_split(self):
        text = "This is a short text."
        parts = _split_text(text, max_tokens=50)
        assert len(parts) == 1
        assert parts[0] == text

    def test_long_text_is_split(self):
        text = " ".join(["word"] * 500)
        parts = _split_text(text, max_tokens=100, overlap_tokens=10)
        assert len(parts) > 1
        for part in parts:
            assert _approx_token_count(part) <= 110  # allow slight overshoot

    def test_overlap_exists(self):
        text = " ".join(["word"] * 300)
        parts = _split_text(text, max_tokens=100, overlap_tokens=20)
        assert len(parts) >= 2
        # The end of part 0 should partially overlap with the start of part 1
        end_tokens = parts[0].split()[-20:]
        start_tokens = parts[1].split()[:20]
        # At least some overlap expected
        overlap = set(end_tokens) & set(start_tokens)
        assert len(overlap) > 0


# ---------------------------------------------------------------------------
# Main chunking function
# ---------------------------------------------------------------------------

class TestChunkFund:
    def test_produces_chunks(self, sample_fund: ScrapedFund):
        chunks = chunk_fund(sample_fund)
        assert len(chunks) > 0

    def test_chunk_metadata(self, sample_fund: ScrapedFund):
        chunks = chunk_fund(sample_fund)
        for c in chunks:
            assert c.source_url == sample_fund.source_url
            assert c.scheme_name == sample_fund.scheme_name
            assert c.scraped_at == sample_fund.scraped_at
            assert c.section != ""
            assert c.chunk_id != ""

    def test_chunk_text_not_empty(self, sample_fund: ScrapedFund):
        chunks = chunk_fund(sample_fund)
        for c in chunks:
            assert c.text.strip() != ""

    def test_idempotent(self, sample_fund: ScrapedFund):
        """Running chunk_fund twice should produce identical chunk IDs."""
        chunks1 = chunk_fund(sample_fund)
        chunks2 = chunk_fund(sample_fund)
        ids1 = [c.chunk_id for c in chunks1]
        ids2 = [c.chunk_id for c in chunks2]
        assert ids1 == ids2

    def test_to_dict(self, sample_fund: ScrapedFund):
        chunks = chunk_fund(sample_fund)
        d = chunks[0].to_dict()
        assert "chunk_id" in d
        assert "text" in d
        assert "source_url" in d
        assert "scheme_name" in d
        assert "section" in d
        assert "scraped_at" in d

    def test_minimal_fund_produces_chunks(self, minimal_fund: ScrapedFund):
        chunks = chunk_fund(minimal_fund)
        assert len(chunks) >= 1  # At least an Overview chunk


class TestChunkAllFunds:
    def test_multiple_funds(self, sample_fund: ScrapedFund, minimal_fund: ScrapedFund):
        chunks = chunk_all_funds([sample_fund, minimal_fund])
        scheme_names = {c.scheme_name for c in chunks}
        assert len(scheme_names) == 2

    def test_empty_list(self):
        chunks = chunk_all_funds([])
        assert chunks == []
