"""
Refusal handler module — returns polite refusals for advisory and out-of-scope queries,
and friendly responses for small-talk.

Ensures absolute compliance by politely refusing to answer non-factual,
speculative, or advisory queries, and redirecting users to official SEBI/AMFI resources.
"""

from __future__ import annotations

import re

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

# ── Small-talk responses — friendly, warm, no citations ───────────
_GREETING_RESPONSES = [
    "Hello! I'm Fundpedia AI — your HDFC Mutual Fund facts assistant. "
    "Ask me about NAV, expense ratios, exit loads, fund managers, or any scheme detail!",
]

_META_RESPONSES = [
    "I can answer factual questions about HDFC Mutual Fund schemes — things like NAV, AUM, "
    "expense ratios, exit loads, minimum SIP amounts, fund managers, and more. "
    "Just ask away!",
]

_THANKS_RESPONSES = [
    "You're welcome! Let me know if you have any other questions about HDFC Mutual Fund schemes.",
]

_FAREWELL_RESPONSES = [
    "Goodbye! Feel free to come back anytime you need info on HDFC Mutual Fund schemes.",
]

_ACKNOWLEDGE_RESPONSES = [
    "Got it! Let me know if there's anything else you'd like to know about HDFC Mutual Fund schemes.",
]

# Patterns to sub-classify small talk
_GREETING_PATTERNS = [
    r"^\s*(?:hi|hello|hey|yo|hola|namaste|howdy|sup|hii+)\s*[!.?]*\s*$",
    r"^\s*(?:good\s+(?:morning|afternoon|evening|night|day))\s*[!.?]*\s*$",
    r"^\s*(?:what'?s?\s+up|how\s+are\s+you|how\s+do\s+you\s+do)\s*[!.?]*\s*$",
]

_META_PATTERNS = [
    r"\bwhat\s+(?:can|do)\s+you\s+(?:do|help|answer|know)\b",
    r"\bwho\s+are\s+you\b",
    r"\bwhat\s+are\s+you\b",
    r"^\s*help\s*[!.?]*\s*$",
    r"\btell\s+me\s+about\s+yourself\b",
    r"\bwhat\s+(?:is|are)\s+your\s+(?:capabilities|features|purpose)\b",
]

_THANKS_PATTERNS = [
    r"^\s*(?:thanks?|thank\s+you|thx|ty|cheers|appreciated|great)\s*[!.?]*\s*$",
    r"\bthanks?\s+(?:a\s+lot|so\s+much|very\s+much)\b",
]

_FAREWELL_PATTERNS = [
    r"^\s*(?:bye|goodbye|see\s+you|later|take\s+care)\s*[!.?]*\s*$",
]


def _classify_small_talk(query: str) -> str:
    """Sub-classify small talk into greeting / meta / thanks / farewell / acknowledge."""
    s = query.strip().lower()
    for p in _GREETING_PATTERNS:
        if re.search(p, s):
            return "greeting"
    for p in _META_PATTERNS:
        if re.search(p, s):
            return "meta"
    for p in _THANKS_PATTERNS:
        if re.search(p, s):
            return "thanks"
    for p in _FAREWELL_PATTERNS:
        if re.search(p, s):
            return "farewell"
    return "acknowledge"


def handle_small_talk(query: str) -> ChatResponse:
    """
    Generate a friendly ChatResponse for small-talk queries.
    No retrieval, no citation, no AMFI disclaimer.
    """
    sub_type = _classify_small_talk(query)

    if sub_type == "greeting":
        text = _GREETING_RESPONSES[0]
    elif sub_type == "meta":
        text = _META_RESPONSES[0]
    elif sub_type == "thanks":
        text = _THANKS_RESPONSES[0]
    elif sub_type == "farewell":
        text = _FAREWELL_RESPONSES[0]
    else:
        text = _ACKNOWLEDGE_RESPONSES[0]

    return ChatResponse(
        answer=text,
        citation=CitationInfo(),
        footer="Fundpedia AI",
        query_type="small_talk",
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
