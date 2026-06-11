"""
Refusal handler module — returns polite refusals for advisory and out-of-scope queries.

Ensures absolute compliance by politely refusing to answer non-factual,
speculative, or advisory queries, and redirecting users to official SEBI/AMFI resources.
"""

from __future__ import annotations

from app.api.schemas import CitationInfo, ChatResponse

ADVISORY_REFUSAL_TEXT = (
    "I can only provide factual information about HDFC Mutual Fund schemes. "
    "For financial advice, investment guidance, or fund comparisons, please consult a "
    "SEBI-registered financial advisor or visit the Association of Mutual Funds in India (AMFI) at "
    "https://www.amfiindia.com."
)

OUT_OF_SCOPE_REFUSAL_TEXT = (
    "I can only answer factual questions regarding HDFC Mutual Fund schemes (such as expense ratios, "
    "exit loads, NAV, AUM, and fund managers). For other topics, please consult appropriate resources."
)


def handle_refusal(query_type: str) -> ChatResponse:
    """
    Generate a formatted ChatResponse for a refused query.
    
    Args:
        query_type: The classification of the query ('advisory' or 'out_of_scope').
    """
    if query_type == "advisory":
        return ChatResponse(
            answer=ADVISORY_REFUSAL_TEXT,
            citation=CitationInfo(
                source_url="https://www.amfiindia.com",
                scheme_name="AMFI India",
                section="Investor Education",
            ),
            footer="Association of Mutual Funds in India",
            query_type="advisory",
        )
    else:
        # out_of_scope fallback
        return ChatResponse(
            answer=OUT_OF_SCOPE_REFUSAL_TEXT,
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="out_of_scope",
        )
