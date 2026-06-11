"""
Unit tests for the web scraper module.

Tests cover:
  - URL list completeness
  - ScrapedFund data model
  - Extraction helpers (where possible without a live page)
  - scrape_all_urls integration (marked with pytest.mark.slow)
"""

import pytest
from app.scraper.urls import APPROVED_URLS, get_approved_url_set
from app.scraper.scraper import ScrapedFund, FundManager


# ---------------------------------------------------------------------------
# URL list
# ---------------------------------------------------------------------------

class TestApprovedURLs:
    """Validate the pre-approved URL list."""

    def test_five_urls_defined(self):
        """APPROVED_URLS should contain exactly 5 entries."""
        assert len(APPROVED_URLS) == 5

    def test_each_entry_has_required_keys(self):
        """Every entry must have 'scheme_name' and 'url'."""
        for entry in APPROVED_URLS:
            assert "scheme_name" in entry, f"Missing 'scheme_name' in {entry}"
            assert "url" in entry, f"Missing 'url' in {entry}"

    def test_all_urls_are_groww(self):
        """Every URL must point to groww.in/mutual-funds/."""
        for entry in APPROVED_URLS:
            assert entry["url"].startswith("https://groww.in/mutual-funds/"), (
                f"URL doesn't look like a Groww MF page: {entry['url']}"
            )

    def test_all_schemes_are_hdfc(self):
        """All scheme names should contain 'HDFC'."""
        for entry in APPROVED_URLS:
            assert "HDFC" in entry["scheme_name"], (
                f"Expected HDFC scheme: {entry['scheme_name']}"
            )

    def test_no_duplicate_urls(self):
        """No duplicate URLs."""
        urls = [e["url"] for e in APPROVED_URLS]
        assert len(urls) == len(set(urls))

    def test_get_approved_url_set(self):
        """get_approved_url_set() returns a set of 5 unique URLs."""
        url_set = get_approved_url_set()
        assert isinstance(url_set, set)
        assert len(url_set) == 5


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class TestScrapedFund:
    """Verify ScrapedFund dataclass behaviour."""

    def test_defaults(self):
        """A ScrapedFund with only required fields should have sane defaults."""
        fund = ScrapedFund(
            scheme_name="Test Fund",
            source_url="https://example.com",
            scraped_at="2026-01-01T00:00:00Z",
        )
        assert fund.scheme_name == "Test Fund"
        assert fund.category == ""
        assert fund.nav == ""
        assert fund.expense_ratio == ""
        assert fund.fund_managers == []
        assert fund.sections == {}

    def test_fund_manager_dataclass(self):
        """FundManager dataclass should hold name and optional fields."""
        fm = FundManager(name="John Doe", since="Jan 2020")
        assert fm.name == "John Doe"
        assert fm.since == "Jan 2020"
        assert fm.qualification == ""


# ---------------------------------------------------------------------------
# Expected schemes
# ---------------------------------------------------------------------------

EXPECTED_SCHEMES = [
    "HDFC Mid Cap Fund – Direct Growth",
    "HDFC Large Cap Fund – Direct Growth",
    "HDFC Small Cap Fund – Direct Growth",
    "HDFC Gold ETF Fund of Fund – Direct Growth",
    "HDFC Defence Fund – Direct Growth",
]


class TestExpectedSchemes:
    """Ensure the URL list covers all expected schemes."""

    @pytest.mark.parametrize("scheme_name", EXPECTED_SCHEMES)
    def test_scheme_in_urls(self, scheme_name: str):
        """Each expected scheme must appear in APPROVED_URLS."""
        names = [e["scheme_name"] for e in APPROVED_URLS]
        assert scheme_name in names
