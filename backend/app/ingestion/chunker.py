"""
Document chunking module — converts ScrapedFund data into retrieval-friendly
text chunks with full source metadata.

Strategy:
  1.  Convert each ScrapedFund into *section-aware text blocks*.
  2.  Split long blocks into ~300-500 token chunks with ~50-token overlap.
  3.  Attach metadata (source_url, scheme_name, section, scraped_at) to each.
  4.  Generate deterministic chunk IDs (scheme-slug + section + index) so
      re-running the ingestion is idempotent.
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass, field
from typing import Sequence

from app.config import settings
from app.scraper.models import ScrapedFund

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """A single retrieval-ready text chunk with metadata."""

    chunk_id: str
    text: str
    source_url: str
    scheme_name: str
    section: str
    scraped_at: str

    def to_dict(self) -> dict:
        """Serialise for ChromaDB / JSON storage."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_url": self.source_url,
            "scheme_name": self.scheme_name,
            "section": self.section,
            "scraped_at": self.scraped_at,
        }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKEN_APPROX_RE = re.compile(r"\S+")     # whitespace-delimited "tokens"


def _approx_token_count(text: str) -> int:
    """Cheap whitespace-based token count (good enough for chunking)."""
    return len(_TOKEN_APPROX_RE.findall(text))


def _slugify(name: str) -> str:
    """Convert a scheme name into a short kebab-case slug."""
    s = name.lower()
    s = s.replace("\u2013", "-").replace("\u2014", "-")  # en-dash / em-dash
    s = re.sub(r"[^a-z0-9\s-]", "", s)    # strip special chars
    s = re.sub(r"\s+", "-", s).strip("-")
    # Remove consecutive hyphens
    s = re.sub(r"-{2,}", "-", s)
    # Keep it short
    parts = s.split("-")
    return "-".join(parts[:5])             # e.g. "hdfc-mid-cap-fund-direct"


def _make_chunk_id(slug: str, section: str, index: int) -> str:
    """Deterministic chunk ID: slug-section_hash-index."""
    sec_hash = hashlib.md5(section.encode()).hexdigest()[:6]
    return f"{slug}-{sec_hash}-{index:03d}"


# ---------------------------------------------------------------------------
# Section builder — ScrapedFund → list[(section_name, text)]
# ---------------------------------------------------------------------------

def _build_sections(fund: ScrapedFund) -> list[tuple[str, str]]:
    """
    Convert a ScrapedFund into a list of (section_name, prose_text) pairs.

    Each block is a self-contained passage that makes sense on its own
    (important for retrieval quality).
    """
    sections: list[tuple[str, str]] = []

    # 1. Overview block
    overview_parts = [f"{fund.scheme_name}"]
    if fund.category or fund.sub_category:
        overview_parts.append(
            f"Category: {fund.category}"
            + (f" — {fund.sub_category}" if fund.sub_category else "")
        )
    if fund.risk_level:
        overview_parts.append(f"Risk level: {fund.risk_level}")
    if fund.fund_house:
        overview_parts.append(f"Fund house: {fund.fund_house}")
    if fund.launch_date:
        overview_parts.append(f"Launch date: {fund.launch_date}")
    if fund.benchmark:
        overview_parts.append(f"Benchmark index: {fund.benchmark}")
    sections.append(("Overview", "\n".join(overview_parts)))

    # 2. NAV & Key Stats
    stats_parts = [f"Key statistics for {fund.scheme_name}:"]
    if fund.nav:
        nav_info = f"NAV: {fund.nav}"
        if fund.nav_date:
            nav_info += f" (as of {fund.nav_date})"
        stats_parts.append(nav_info)
    if fund.aum:
        stats_parts.append(f"Fund size (AUM): {fund.aum}")
    if fund.expense_ratio:
        stats_parts.append(f"Expense ratio: {fund.expense_ratio}")
    if fund.rating:
        stats_parts.append(f"Rating: {fund.rating} stars")
    if fund.min_sip:
        stats_parts.append(f"Minimum SIP amount: {fund.min_sip}")
    if fund.min_lumpsum:
        stats_parts.append(f"Minimum lumpsum investment: {fund.min_lumpsum}")
    if len(stats_parts) > 1:
        sections.append(("Fund Details", "\n".join(stats_parts)))

    # 3. Exit Load & Tax
    exit_parts = [f"Exit load and charges for {fund.scheme_name}:"]
    if fund.exit_load:
        exit_parts.append(f"Exit load: {fund.exit_load}")
    if fund.lock_in_period:
        exit_parts.append(f"Lock-in period: {fund.lock_in_period}")
    else:
        exit_parts.append("Lock-in period: No lock-in period")
    if fund.stamp_duty:
        exit_parts.append(f"Stamp duty: {fund.stamp_duty}")
    if len(exit_parts) > 1:
        sections.append(("Exit Load", "\n".join(exit_parts)))

    # 4. Fund Managers
    if fund.fund_managers:
        fm_parts = [f"Fund managers of {fund.scheme_name}:"]
        for fm in fund.fund_managers:
            line = f"- {fm.name}"
            if fm.since:
                line += f" (managing since {fm.since})"
            if fm.qualification:
                line += f", {fm.qualification}"
            if fm.experience:
                line += f", {fm.experience}"
            fm_parts.append(line)
        sections.append(("Fund Managers", "\n".join(fm_parts)))

    # 5. Returns
    ret_parts = [f"Historical returns for {fund.scheme_name}:"]
    any_return = False
    if fund.returns_1y:
        ret_parts.append(f"1-year return: {fund.returns_1y}")
        any_return = True
    if fund.returns_3y:
        ret_parts.append(f"3-year annualised return: {fund.returns_3y}")
        any_return = True
    if fund.returns_5y:
        ret_parts.append(f"5-year annualised return: {fund.returns_5y}")
        any_return = True
    if any_return:
        sections.append(("Returns", "\n".join(ret_parts)))

    # 6. About & Investment Objective
    if fund.about:
        sections.append(("About", f"About {fund.scheme_name}:\n{fund.about}"))
    if fund.investment_objective:
        sections.append((
            "Investment Objective",
            f"Investment objective of {fund.scheme_name}:\n{fund.investment_objective}",
        ))

    # 7. Any additional raw sections not already covered
    known = {"Exit Load & Tax", "Fund Managers", "About", "Fund House", "Minimum Investments"}
    for sec_name, sec_text in fund.sections.items():
        if sec_name not in known and sec_text.strip():
            sections.append((sec_name, sec_text.strip()))

    return sections


# ---------------------------------------------------------------------------
# Text splitter
# ---------------------------------------------------------------------------

def _split_text(
    text: str,
    max_tokens: int = 400,
    overlap_tokens: int = 50,
) -> list[str]:
    """
    Split *text* into chunks of at most *max_tokens* (whitespace-counted)
    with *overlap_tokens* overlap.

    Tries to split on paragraph boundaries first, then sentence boundaries,
    then word boundaries.
    """
    if _approx_token_count(text) <= max_tokens:
        return [text]

    # Split into paragraphs first
    paragraphs = re.split(r"\n{2,}", text)

    # If the text is a single paragraph exceeding max_tokens, split by sentences
    if len(paragraphs) <= 1:
        return _split_by_sentences(text, max_tokens, overlap_tokens)

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _approx_token_count(para)

        if current_tokens + para_tokens <= max_tokens:
            current.append(para)
            current_tokens += para_tokens
        else:
            if current:
                chunks.append("\n\n".join(current))
            # If a single paragraph exceeds max_tokens, split it by sentences
            if para_tokens > max_tokens:
                sub_chunks = _split_by_sentences(para, max_tokens, overlap_tokens)
                chunks.extend(sub_chunks)
                current = []
                current_tokens = 0
            else:
                # Start new chunk with overlap from previous
                overlap_text = _get_tail_overlap(
                    "\n\n".join(current) if current else "", overlap_tokens
                )
                current = [overlap_text, para] if overlap_text else [para]
                current_tokens = _approx_token_count("\n\n".join(current))

    if current:
        chunks.append("\n\n".join(current))

    return [c.strip() for c in chunks if c.strip()]


def _split_by_sentences(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split text by sentence boundaries, falling back to word-level."""
    sentences = re.split(r"(?<=[.!?])\s+", text)

    # If no sentence boundaries found, fall back to word-level splitting
    if len(sentences) <= 1 and _approx_token_count(text) > max_tokens:
        return _split_by_words(text, max_tokens, overlap_tokens)

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = _approx_token_count(sent)
        # If a single sentence exceeds max_tokens, split it by words
        if sent_tokens > max_tokens:
            if current:
                chunks.append(" ".join(current))
                current = []
                current_tokens = 0
            chunks.extend(_split_by_words(sent, max_tokens, overlap_tokens))
            continue
        if current_tokens + sent_tokens <= max_tokens:
            current.append(sent)
            current_tokens += sent_tokens
        else:
            if current:
                chunks.append(" ".join(current))
            overlap_text = _get_tail_overlap(" ".join(current) if current else "", overlap_tokens)
            current = [overlap_text, sent] if overlap_text else [sent]
            current_tokens = _approx_token_count(" ".join(current))

    if current:
        chunks.append(" ".join(current))

    return chunks


def _split_by_words(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split text at word boundaries when no sentence/paragraph breaks exist."""
    words = text.split()
    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        # Advance past current chunk minus overlap
        start += max_tokens - overlap_tokens
        if start >= len(words):
            break

    return [c for c in chunks if c.strip()]



def _get_tail_overlap(text: str, overlap_tokens: int) -> str:
    """Return the last *overlap_tokens* whitespace-tokens of *text*."""
    if not text or overlap_tokens <= 0:
        return ""
    tokens = text.split()
    tail = tokens[-overlap_tokens:]
    return " ".join(tail)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def chunk_fund(
    fund: ScrapedFund,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """
    Convert a single ScrapedFund into a list of retrieval-ready `Chunk`s.

    Each chunk:
      - Has deterministic `chunk_id` (idempotent re-ingestion).
      - Carries full metadata (`source_url`, `scheme_name`, `section`, `scraped_at`).
      - Is between ~100-500 tokens (configurable).
    """
    _size = chunk_size or settings.chunk_size
    _overlap = chunk_overlap or settings.chunk_overlap

    slug = _slugify(fund.scheme_name)
    sections = _build_sections(fund)
    chunks: list[Chunk] = []

    for section_name, section_text in sections:
        if not section_text.strip():
            continue
        text_parts = _split_text(section_text, max_tokens=_size, overlap_tokens=_overlap)
        for idx, part in enumerate(text_parts):
            chunks.append(Chunk(
                chunk_id=_make_chunk_id(slug, section_name, idx),
                text=part,
                source_url=fund.source_url,
                scheme_name=fund.scheme_name,
                section=section_name,
                scraped_at=fund.scraped_at,
            ))

    return chunks


def chunk_all_funds(
    funds: Sequence[ScrapedFund],
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Chunk every fund and return a flat list of all Chunks."""
    all_chunks: list[Chunk] = []
    for fund in funds:
        all_chunks.extend(chunk_fund(fund, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return all_chunks
