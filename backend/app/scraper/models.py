"""
Data models for the scraper.
Separated from scraper.py to prevent Playwright dependency loading during API server startup.
"""
from dataclasses import dataclass, field

@dataclass
class FundManager:
    """A single fund manager entry."""
    name: str
    since: str = ""               # e.g. "Jan 2013"
    qualification: str = ""
    experience: str = ""


@dataclass
class ScrapedFund:
    """All structured data extracted from one Groww mutual-fund page."""

    # ── Identity ──────────────────────────────────────────────────
    scheme_name: str
    source_url: str
    scraped_at: str                # ISO-8601 UTC timestamp

    # ── Category & Risk ───────────────────────────────────────────
    category: str = ""             # e.g. "Equity"
    sub_category: str = ""         # e.g. "Mid Cap"
    risk_level: str = ""           # e.g. "Very High Risk"

    # ── NAV ───────────────────────────────────────────────────────
    nav: str = ""                  # e.g. "₹219.67"
    nav_date: str = ""             # e.g. "02 Jun '26"

    # ── Key stats ─────────────────────────────────────────────────
    min_sip: str = ""              # e.g. "₹100"
    min_lumpsum: str = ""          # e.g. "₹100"
    aum: str = ""                  # e.g. "₹94,744.72 Cr"
    expense_ratio: str = ""        # e.g. "0.73%"
    rating: str = ""               # e.g. "5"

    # ── Exit load & lock-in ───────────────────────────────────────
    exit_load: str = ""            # e.g. "1% if redeemed within 1 year"
    lock_in_period: str = ""       # e.g. "No lock-in"
    stamp_duty: str = ""           # e.g. "0.005%"

    # ── Fund info ─────────────────────────────────────────────────
    benchmark: str = ""            # e.g. "NIFTY Midcap 150 TRI"
    fund_house: str = ""           # e.g. "HDFC Mutual Fund"
    launch_date: str = ""          # scheme inception date
    fund_managers: list[FundManager] = field(default_factory=list)

    # ── Textual description ───────────────────────────────────────
    about: str = ""                # "About the scheme" paragraph
    investment_objective: str = "" # investment objective text

    # ── Returns (informational, not for advice) ───────────────────
    returns_1y: str = ""
    returns_3y: str = ""
    returns_5y: str = ""

    # ── Raw sections (free-text blocks keyed by section heading) ──
    sections: dict[str, str] = field(default_factory=dict)
