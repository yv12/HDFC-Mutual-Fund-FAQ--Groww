"""
LLM Query Rewriter module.

Pre-processes user queries to:
  1. Resolve pronouns (this scheme, that fund, it) from conversation history.
  2. Normalize slang, aliases, and acronyms to official HDFC Mutual Fund scheme names.
  3. Expand abbreviations and normalize to a plain question.
"""

from __future__ import annotations

import logging
from typing import Any
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def _extract_last_fund_from_history(history: list[dict[str, Any]]) -> str | None:
    """
    Scan conversation history (most-recent first) to find the last fund name mentioned.
    Returns the official fund name string or None.
    """
    FUND_NAMES = [
        "HDFC Mid Cap Fund Direct Growth",
        "HDFC Mid Cap Fund",
        "HDFC Large Cap Fund Direct Growth",
        "HDFC Large Cap Fund",
        "HDFC Small Cap Fund Direct Growth",
        "HDFC Small Cap Fund",
        "HDFC Gold ETF Fund of Fund Direct Plan Growth",
        "HDFC Gold ETF",
        "HDFC Defence Fund Direct Growth",
        "HDFC Defence Fund",
    ]
    # Search from most recent message backwards
    for msg in reversed(history):
        content = msg.get("content", "")
        for name in FUND_NAMES:
            if name.lower() in content.lower():
                return name
    return None


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
