"""
LLM Query Rewriter module.

Pre-processes user queries to automatically resolve slang, aliases, and acronyms
to official HDFC Mutual Fund scheme names before retrieval.
"""

from __future__ import annotations

import logging
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

def rewrite_query(query: str) -> str:
    """
    Rewrite the user's query to normalize fund aliases to official names.
    If no aliases are found, or the query is unrelated, it returns the query intact.
    """
    system_prompt = (
        "You are a mutual fund query normalization assistant. Your ONLY job is to rewrite the user's query.\n"
        "Replace any slang, acronyms, or informal aliases with the official HDFC Mutual Fund scheme names.\n"
        "The official names are:\n"
        "- HDFC Mid Cap Fund Direct Growth\n"
        "- HDFC Large Cap Fund Direct Growth\n"
        "- HDFC Small Cap Fund Direct Growth\n"
        "- HDFC Gold ETF Fund of Fund Direct Plan Growth\n"
        "- HDFC Defence Fund Direct Growth\n\n"
        "Rules:\n"
        "1. Do NOT answer the question. Only output the rewritten question.\n"
        "2. If the user's question does not contain any mutual fund references that need renaming, output the original question exactly as is.\n"
        "3. Do not add any introductory text, quotes, or conversational filler."
    )

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
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        rewritten = completion.choices[0].message.content.strip()
        logger.info("Original Query: '%s' | Rewritten: '%s'", query, rewritten)
        return rewritten
    except Exception as exc:
        logger.error("Query rewriting failed: %s. Falling back to original query.", exc)
        return query
