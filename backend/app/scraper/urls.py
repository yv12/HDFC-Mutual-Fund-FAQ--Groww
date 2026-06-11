"""
Pre-approved URL list for the Mutual Fund FAQ Assistant.

Only these URLs are scraped and indexed. The citation validator
uses this list to verify that all links in responses are legitimate.
"""

# Each entry maps a scheme name to its Groww URL.
APPROVED_URLS: list[dict[str, str]] = [
    {
        "scheme_name": "HDFC Mid Cap Fund – Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Large Cap Fund – Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Small Cap Fund – Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Gold ETF Fund of Fund – Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    },
    {
        "scheme_name": "HDFC Defence Fund – Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
    },
]


def get_approved_url_set() -> set[str]:
    """Return a set of all approved base URLs for fast lookup."""
    return {entry["url"] for entry in APPROVED_URLS}
