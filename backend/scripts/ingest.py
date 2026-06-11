"""
One-time ingestion script.

Orchestrates the full offline pipeline:
  scrape → extract → chunk → save to JSON (Phase 2)
  (Phase 3 will add: embed → store in ChromaDB)

Usage
-----
    cd backend
    python -m scripts.ingest            # scrape all 5 URLs & chunk
    python -m scripts.ingest --dry-run  # scrape & chunk but don't persist
    python -m scripts.ingest --inspect  # print sample chunks to stdout
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so imports work
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.scraper.scraper import scrape_all_urls, ScrapedFund
from app.ingestion.chunker import chunk_all_funds, Chunk

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")


# ---------------------------------------------------------------------------
# Persistence helpers (JSON for now; ChromaDB added in Phase 3)
# ---------------------------------------------------------------------------

_DATA_DIR = _BACKEND_DIR / "data"
_SCRAPED_FILE = _DATA_DIR / "scraped_funds.json"
_CHUNKS_FILE = _DATA_DIR / "chunks.json"


def _save_scraped(funds: list[ScrapedFund]) -> Path:
    """Persist raw scraped data as JSON for debugging / re-use."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    from dataclasses import asdict
    data = [asdict(f) for f in funds]
    _SCRAPED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %d scraped funds → %s", len(funds), _SCRAPED_FILE)
    return _SCRAPED_FILE


def _save_chunks(chunks: list[Chunk]) -> Path:
    """Persist chunks as JSON.  IDs are deterministic → file is idempotent."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = [c.to_dict() for c in chunks]
    _CHUNKS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved %d chunks → %s", len(chunks), _CHUNKS_FILE)
    return _CHUNKS_FILE


def _save_preview(chunks: list[Chunk]) -> Path:
    """Save a human-readable markdown preview of the chunks grouped by fund."""
    preview_file = _DATA_DIR / "chunks_preview.md"
    from collections import defaultdict
    grouped = defaultdict(list)
    for c in chunks:
        grouped[c.scheme_name].append(c)
        
    lines = []
    lines.append("# Chunking Preview")
    lines.append(f"This file details the generated chunks for inspection. Total chunks: {len(chunks)}")
    lines.append("")
    
    for scheme_name, scheme_chunks in grouped.items():
        lines.append(f"## {scheme_name}")
        lines.append(f"Total Chunks: {len(scheme_chunks)}")
        lines.append("")
        for idx, c in enumerate(scheme_chunks):
            lines.append(f"### Chunk {idx + 1}: {c.chunk_id}")
            lines.append(f"- **Section**: {c.section}")
            lines.append(f"- **Source URL**: [{c.source_url}]({c.source_url})")
            lines.append(f"- **Approx. Tokens**: {len(c.text.split())}")
            lines.append("")
            lines.append("```text")
            lines.append(c.text)
            lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")
            
    preview_file.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Saved chunking preview → %s", preview_file)
    return preview_file



# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(*, dry_run: bool = False, inspect: bool = False) -> list[Chunk]:
    """
    Execute the full offline ingestion pipeline:

    1. Scrape all 5 Groww URLs via Playwright.
    2. Chunk the extracted data into retrieval-ready text blocks.
    3. Persist scraped data + chunks as JSON (unless --dry-run).
    4. Print sample chunks (if --inspect).

    Returns the list of generated chunks.
    """
    # ── Step 1: Scrape ────────────────────────────────────────────
    logger.info("═══ PHASE 2.1 — Scraping %d URLs ═══", 5)
    funds = await scrape_all_urls()

    if not funds:
        logger.error("No funds were scraped — aborting.")
        return []

    logger.info(
        "Scraped %d / 5 funds successfully.", len(funds),
    )

    # Quick summary
    for f in funds:
        logger.info(
            "  • %s  |  NAV=%s  AUM=%s  Expense=%s  Managers=%d",
            f.scheme_name, f.nav, f.aum, f.expense_ratio, len(f.fund_managers),
        )

    # ── Step 2: Chunk ─────────────────────────────────────────────
    logger.info("═══ PHASE 2.5 — Chunking ═══")
    chunks = chunk_all_funds(funds)
    logger.info("Generated %d chunks from %d funds.", len(chunks), len(funds))

    # Per-fund breakdown
    from collections import Counter
    fund_counts = Counter(c.scheme_name for c in chunks)
    for name, count in fund_counts.items():
        logger.info("  • %s → %d chunks", name, count)

    # ── Step 3: Inspect (optional) ────────────────────────────────
    if inspect:
        logger.info("═══ Sample Chunks (first 3) ═══")
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        for c in chunks[:3]:
            try:
                print(f"\n{'-' * 60}")
                print(f"ID:      {c.chunk_id}")
                print(f"Section: {c.section}")
                print(f"Scheme:  {c.scheme_name}")
                print(f"URL:     {c.source_url}")
                print(f"Text:\n{c.text}")
                print(f"{'-' * 60}")
            except Exception:
                # Safe ASCII fallback printing
                safe_text = c.text.encode("ascii", errors="replace").decode("ascii")
                print(f"\n{'-' * 60}")
                print(f"ID:      {c.chunk_id}")
                print(f"Section: {c.section}")
                print(f"Scheme:  {c.scheme_name.encode('ascii', errors='replace').decode('ascii')}")
                print(f"URL:     {c.source_url}")
                print(f"Text:\n{safe_text}")
                print(f"{'-' * 60}")

    # ── Step 4: Persist ───────────────────────────────────────────
    if not dry_run:
        _save_scraped(funds)
        _save_chunks(chunks)
        _save_preview(chunks)
        
        # Index chunks in persistent ChromaDB vector store
        logger.info("═══ PHASE 3 — Vector Store Indexing ═══")
        try:
            from app.ingestion.vector_store import add_chunks, reset_store
            
            reset_store()  # Clear collection for clean, duplicate-free indexing
            add_chunks(chunks)
            logger.info("✓ Indexed all chunks in ChromaDB successfully.")
        except Exception as exc:
            logger.error("Failed to index chunks in ChromaDB: %s", exc)
            
        logger.info("✓ Ingestion complete. Files saved to %s", _DATA_DIR)
    else:
        logger.info("✓ Dry-run complete.  No files written.")

    return chunks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mutual Fund FAQ Assistant — Offline Ingestion Pipeline",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and chunk but do not persist any files.",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Print sample chunks to stdout after chunking.",
    )
    args = parser.parse_args()

    asyncio.run(run_pipeline(dry_run=args.dry_run, inspect=args.inspect))


if __name__ == "__main__":
    main()
