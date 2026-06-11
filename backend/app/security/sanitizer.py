"""
Input sanitization module — strips potential prompt injection attempts
and limits query length for system protection.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# List of regexes to detect and strip common prompt injection phrases
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"bypass\s+restrictions", re.IGNORECASE),
    re.compile(r"bypass\s+safety", re.IGNORECASE),
    re.compile(r"instead\s+of\s+(?:your|the)\s+instructions", re.IGNORECASE),
]


def sanitize_input(query: str, max_length: int = 500) -> str:
    """
    Sanitize the input query to protect against prompt injection and limit length.

    Args:
        query: Raw input string from the user.
        max_length: Maximum allowed character length.

    Returns:
        Sanitized and trimmed query string.
    """
    # 1. Trim whitespaces
    cleaned = query.strip()

    # 2. Limit length
    if len(cleaned) > max_length:
        logger.warning("Input query length %d exceeds max %d, truncating.", len(cleaned), max_length)
        cleaned = cleaned[:max_length]

    # 3. Strip prompt injection keywords
    sanitized = cleaned
    for pattern in INJECTION_PATTERNS:
        if pattern.search(sanitized):
            logger.warning("Sanitization: Stripping detected prompt injection pattern: %s", pattern.pattern)
            sanitized = pattern.sub("", sanitized)

    # Clean up duplicate spaces that might have been left by stripping
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    return sanitized
