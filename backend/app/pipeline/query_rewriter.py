"""
LLM Query Rewriter module.

Pre-processes user queries to:
  1. Resolve pronouns (this scheme, that fund, it) from conversation history.
  2. Normalize slang, aliases, and acronyms to official HDFC Mutual Fund scheme names.
  3. Expand abbreviations and normalize to a plain question.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

OFFICIAL_SCHEMES = [
    {"display": "HDFC Mid Cap Fund", "official": "HDFC Mid Cap Fund Direct Growth"},
    {"display": "HDFC Large Cap Fund (Top 100)", "official": "HDFC Large Cap Fund Direct Growth"},
    {"display": "HDFC Small Cap Fund", "official": "HDFC Small Cap Fund Direct Growth"},
    {"display": "HDFC Defence Fund", "official": "HDFC Defence Fund Direct Growth"},
    {"display": "HDFC Gold ETF", "official": "HDFC Gold ETF Fund of Fund Direct Plan Growth"},
]

SCHEME_KEYWORD_PATTERNS = [
    (r"\b(mid\s*cap|midcap|opportunities)\b", "HDFC Mid Cap Fund Direct Growth"),
    (r"\b(large\s*cap|largecap|top\s*100|top100)\b", "HDFC Large Cap Fund Direct Growth"),
    (r"\b(small\s*cap|smallcap)\b", "HDFC Small Cap Fund Direct Growth"),
    (r"\b(gold|gold\s*etf)\b", "HDFC Gold ETF Fund of Fund Direct Plan Growth"),
    (r"\b(defence|defense)\b", "HDFC Defence Fund Direct Growth"),
]

SCHEME_ATTRIBUTES = [
    (r"\b(exit\s*load)\b", "Exit load"),
    (r"\b(expense\s*ratio|fees?|charges?)\b", "Expense ratio"),
    (r"\b(nav|net\s*asset\s*value)\b", "NAV"),
    (r"\b(aum|fund\s*size|assets\s*under\s*management)\b", "AUM"),
    (r"\b(returns?|cagr|performance|past\s*returns?)\b", "Returns"),
    (r"\b(portfolio|holdings?|stocks?|sector\s*allocation|top\s*holdings?)\b", "Portfolio holdings"),
    (r"\b(fund\s*manager|manager|who\s*manages)\b", "Fund manager"),
    (r"\b(min(?:imum)?\s*sip|sip\s*amount|min(?:imum)?\s*investment)\b", "Minimum SIP"),
    (r"\b(lock[\s-]*in|lockin|lockin\s*period)\b", "Lock-in period"),
    (r"\b(stamp\s*duty|tax|taxation)\b", "Taxation & stamp duty"),
    (r"\b(factsheet|benchmark|objective)\b", "Overview"),
]

PRONOUN_TRIGGERS = [
    r"\b(this\s*scheme|this\s*fund|that\s*scheme|that\s*fund|the\s*scheme|the\s*fund|this\s*one|that\s*one)\b",
    r"\b(its\s*exit\s*load|its\s*expense\s*ratio|its\s*nav|its\s*aum|its\s*return|its\s*portfolio)\b",
    r"\b(tell\s*me\s*about\s*it|details\s*of\s*it|info\s*on\s*it)\b",
]


def extract_fund_from_text(text: str) -> str | None:
    """Check if any known HDFC scheme or alias is mentioned in text."""
    if not text:
        return None
    s = text.lower()
    for pattern, official_name in SCHEME_KEYWORD_PATTERNS:
        if re.search(pattern, s, re.IGNORECASE):
            return official_name
    for scheme in OFFICIAL_SCHEMES:
        if scheme["official"].lower() in s or scheme["display"].lower() in s:
            return scheme["official"]
    return None


def _extract_last_fund_from_history(history: list[dict[str, Any]]) -> str | None:
    """
    Scan conversation history (most-recent first) to find the last fund name or alias mentioned.
    Returns the official fund name string or None.
    """
    if not history:
        return None

    # Search backwards from most recent message
    for msg in reversed(history):
        content = msg.get("content", "")
        fund = extract_fund_from_text(content)
        if fund:
            return fund
    return None


def detect_ambiguous_scheme_query(
    query: str, history: list[dict[str, Any]] | None = None
) -> tuple[bool, str | None, list[str]]:
    """
    Detect if the user is asking a scheme-specific question without specifying which scheme,
    and no scheme can be determined from session history.

    Returns:
        (is_ambiguous, detected_attribute, options_list)
    """
    history = history or []
    s = query.lower()

    # 1. Check if the query itself specifies a fund
    if extract_fund_from_text(query):
        return False, None, []

    # 2. Check if history specifies a fund
    if _extract_last_fund_from_history(history):
        return False, None, []

    # 3. Check for pronoun triggers
    has_pronoun = any(re.search(pat, s, re.IGNORECASE) for pat in PRONOUN_TRIGGERS)

    # 4. Check for scheme attributes
    detected_attr = None
    for pat, attr_name in SCHEME_ATTRIBUTES:
        if re.search(pat, s, re.IGNORECASE):
            detected_attr = attr_name
            break

    # If the query contains a pronoun or asks for a scheme-specific attribute without a scheme:
    if has_pronoun or detected_attr:
        if detected_attr:
            options = [f"{detected_attr} of {scheme['display']}" for scheme in OFFICIAL_SCHEMES]
        else:
            options = [f"Tell me about {scheme['display']}" for scheme in OFFICIAL_SCHEMES]
        return True, detected_attr, options

    return False, None, []


def _build_history_context(history: list[dict[str, Any]]) -> str:
    """Build a compact summary of recent conversation for the rewriter."""
    if not history:
        return ""
    
    # Take last 4 messages max
    recent = history[-4:]
    lines = []
    for msg in recent:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        # Truncate long messages
        if len(content) > 200:
            content = content[:200] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def rewrite_query(query: str, history: list[dict[str, Any]] | None = None) -> str:
    """
    Rewrite the user's query to:
      1. Resolve pronouns using conversation history (this scheme → HDFC Mid Cap Fund)
      2. Normalize fund aliases to official names
      3. Expand abbreviations
    
    If no changes are needed, returns the query intact.
    """
    history = history or []
    
    history_context = _build_history_context(history)
    last_fund = _extract_last_fund_from_history(history)
    
    # Build the system prompt with history awareness
    system_prompt = (
        "You are a mutual fund query normalization assistant. Your ONLY job is to rewrite the user's query.\n"
        "You must:\n"
        "1. Resolve pronouns and vague references using the conversation history below.\n"
        "   - 'this scheme', 'that fund', 'it', 'this one', 'the same fund' → replace with the actual fund name from history.\n"
        "   - If the new query is just a fund name (e.g. 'HDFC Large Cap Fund') and the conversation history asked for a specific attribute (like expense ratio, exit load, NAV, returns, fund manager), carry that attribute over (e.g. 'Expense ratio of HDFC Large Cap Fund Direct Growth').\n"
        "2. Replace any slang, acronyms, or informal aliases with the official HDFC Mutual Fund scheme names.\n"
        "3. Expand abbreviations (e.g., 'ER' → 'expense ratio', 'AUM' → keep as AUM).\n"
        "4. Normalize to a clear, plain question.\n\n"
        "The official names are:\n"
        "- HDFC Mid Cap Fund Direct Growth\n"
        "- HDFC Large Cap Fund Direct Growth\n"
        "- HDFC Small Cap Fund Direct Growth\n"
        "- HDFC Gold ETF Fund of Fund Direct Plan Growth\n"
        "- HDFC Defence Fund Direct Growth\n\n"
    )
    
    if last_fund:
        system_prompt += f"The most recently discussed fund is: {last_fund}\n\n"
    
    system_prompt += (
        "Rules:\n"
        "1. Do NOT answer the question. Only output the rewritten question.\n"
        "2. If the user's question does not contain any references that need resolving, output the original question exactly as is.\n"
        "3. Do not add any introductory text, quotes, or conversational filler.\n"
        "4. Output ONLY the rewritten question, nothing else."
    )

    # Build the user content with history
    user_content = query
    if history_context:
        user_content = f"Conversation history:\n{history_context}\n\nNew query to rewrite: {query}"

    api_key = settings.xai_api_key or "ollama"
    client = OpenAI(
        base_url=settings.xai_base_url,
        api_key=api_key,
        timeout=10.0,
    )

    try:
        logger.debug("Requesting LLM query rewrite using model '%s'", settings.llm_model)
        completion = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        rewritten = (completion.choices[0].message.content or "").strip()
        # Strip any quotes the LLM might have added
        rewritten = rewritten.strip('"\'')
        logger.info("Original Query: '%s' | Rewritten: '%s'", query, rewritten)
        return rewritten if rewritten else query
    except Exception as exc:
        logger.error("Query rewriting failed: %s. Falling back to original query.", exc)
        return query
