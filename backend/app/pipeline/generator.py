"""
LLM generator module — formats prompts and calls local LLM via Ollama.

Builds a facts-only prompt combining retrieved chunks as context and the
user's question. Invokes the local model via the OpenAI-compatible SDK.
"""

from __future__ import annotations

import logging
from typing import Any
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def generate_response(query: str, chunks: list[dict[str, Any]]) -> str:
    """
    Generate a facts-only, cited answer from retrieved context.
    
    If chunks is empty, returns the default refusal statement directly
    without invoking the LLM (mitigating latency and cost).
    """
    if not chunks:
        return "I don't have this information in my current sources."

    # 1. Format the context blocks
    context_parts = []
    for idx, c in enumerate(chunks):
        meta = c.get("metadata", {})
        context_parts.append(
            f"[Source {idx + 1}]\n"
            f"Scheme: {meta.get('scheme_name', 'HDFC Scheme')}\n"
            f"URL: {meta.get('source_url', '')}\n"
            f"Section: {meta.get('section', 'General')}\n"
            f"Content:\n{c.get('text', '')}"
        )
    context_str = "\n\n---\n\n".join(context_parts)
    logger.info("Context sent to LLM:\n%s", context_str)

    # 2. Define the strict facts-only system prompt
    system_prompt = (
        "You are a facts-only mutual fund FAQ assistant. You MUST follow these rules strictly:\n"
        "1. Answer ONLY using the provided context. Do NOT use any external knowledge.\n"
        "2. Keep your answer concise: a MAXIMUM of 3 sentences.\n"
        "3. Do NOT provide investment advice, opinions, suggestions, or recommendations.\n"
        "4. Do NOT generate, infer, or construct any URLs on your own.\n"
        "5. If the context clearly does not contain the information needed to answer, say: "
        "'I don't have this information in my current sources.' "
        "However, if the answer can be reasonably understood from the context (for example, "
        "inferring that 30 days falls within a 1-year exit load window), you SHOULD answer.\n"
        "6. Be direct, factual, and professional. Do NOT append any 'Source:', 'Citation:', or 'Last updated' footers to your response."
    )

    user_content = f"Context:\n{context_str}\n\nQuery: {query}"

    # 3. Initialize OpenAI client pointing to Ollama's API endpoint
    api_key = settings.xai_api_key or "ollama"  # OpenAI client requires a non-empty string API key
    client = OpenAI(
        base_url=settings.xai_base_url,
        api_key=api_key,
        timeout=30.0,  # Generous timeout for local CPU execution
    )

    try:
        logger.info(
            "Requesting LLM generation using model '%s' via endpoint '%s' ...",
            settings.llm_model,
            settings.xai_base_url,
        )
        completion = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,  # Max determinism to avoid hallucination
            max_tokens=300,
        )
        response_text = completion.choices[0].message.content.strip()
        logger.info("LLM generation complete.")
        return response_text
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        return "I'm sorry, I encountered an error while processing your request. Please try again."
