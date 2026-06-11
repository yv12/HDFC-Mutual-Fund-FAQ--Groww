"""
PII detection and blocking module.

Implementation in Phase 5:
  - Regex-based detection for PAN, Aadhaar, email, phone, OTP, account numbers
  - Conservative policy: if PII detected anywhere, entire query is blocked
  - Runs before query reaches the RAG pipeline or LLM
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Compile regex patterns for performance
PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
AADHAAR_PATTERN = re.compile(r"\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b")
PHONE_PATTERN = re.compile(r"(\+91[\-\s]?)?[6-9]\d{9}")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
OTP_PATTERN = re.compile(r"\b\d{4,6}\b")
ACCOUNT_PATTERN = re.compile(r"\b\d{9,18}\b")

# Bank-related keywords that trigger account number detection
BANK_KEYWORDS = ["account", "acc", "bank", "balance", "statement", "savings", "current"]


def scan_pii(text: str) -> bool:
    """
    Scan the input text for PII patterns.

    Returns:
        True if any PII is detected, False otherwise.
    """
    s = text.strip()
    s_lower = s.lower()

    # 1. PAN card detection
    if PAN_PATTERN.search(s):
        logger.warning("PII Warning: PAN card pattern matched.")
        return True

    # 2. Aadhaar card detection
    if AADHAAR_PATTERN.search(s):
        logger.warning("PII Warning: Aadhaar pattern matched.")
        return True

    # 3. Email detection
    if EMAIL_PATTERN.search(s):
        logger.warning("PII Warning: Email pattern matched.")
        return True

    # 4. Indian Phone number detection
    # Strip spaces and hyphens to detect numbers formatted with separators
    phone_clean = re.sub(r"[\s\-]", "", s)
    if PHONE_PATTERN.search(phone_clean):
        logger.warning("PII Warning: Phone pattern matched.")
        return True

    # 5. OTP detection (only when "otp" is present in text context)
    if "otp" in s_lower and OTP_PATTERN.search(s):
        logger.warning("PII Warning: OTP pattern matched in context.")
        return True

    # 6. Bank Account number detection (only when bank keywords are present in text context)
    if any(kw in s_lower for kw in BANK_KEYWORDS) and ACCOUNT_PATTERN.search(s):
        logger.warning("PII Warning: Bank account number pattern matched in context.")
        return True

    return False
