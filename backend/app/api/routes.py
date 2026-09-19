"""
API route definitions for the Mutual Fund FAQ Assistant.
"""

import logging
from fastapi import APIRouter, Depends

from app.api.schemas import ChatRequest, CitationInfo, ChatResponse
from app.pipeline.query_classifier import classify_query
from app.pipeline.retriever import retrieve_relevant_context
from app.pipeline.generator import generate_response
from app.pipeline.query_rewriter import rewrite_query
from app.pipeline.citation_validator import validate_citations
from app.pipeline.refusal_handler import handle_refusal, handle_small_talk
from app.security.pii_scanner import scan_pii
from app.security.sanitizer import sanitize_input
from app.security.rate_limiter import rate_limit_dependency
from app.api.history import get_session_history, add_message
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limit_dependency)],
    tags=["Chat"],
)
async def chat(request: ChatRequest):
    """
    Process a user query through the RAG pipeline with safety guardrails.

    Flow:
      query → rate limit check → sanitize input → PII check → classify →
      small_talk (friendly response) OR advisory/out_of_scope (refusal) OR
      factual (retrieve → rewrite → generate → validate citation) → respond
    """
    import app.ingestion.scheduler as scheduler
    if scheduler.IS_SYNCING:
        logger.warning("Chat query rejected because knowledge base sync is in progress.")
        return ChatResponse(
            answer="The knowledge base is currently being updated. Please try again in a few minutes.",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="factual"
        )

    raw_query = request.query
    logger.info("Received chat query of length %d", len(raw_query))

    # 1. Sanitize the input query (length limit and prompt injection cleaning)
    sanitized_query = sanitize_input(raw_query)
    logger.info("Sanitized query: '%s'", sanitized_query)

    # If query becomes empty after sanitization, handle it gracefully
    if not sanitized_query:
        return ChatResponse(
            answer="Please ask a valid factual question regarding HDFC Mutual Fund schemes.",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="out_of_scope",
        )

    # 1.5 Fetch session history
    session_id = request.session_id or str(uuid.uuid4())
    history = get_session_history(session_id)
    logger.info("Fetched %d turns of history for session %s", len(history), session_id)

    # 2. Scan for PII (PAN, Aadhaar, Email, Phone, OTP, Bank Account)
    if scan_pii(sanitized_query):
        logger.warning("Query blocked by PII scanner.")
        return ChatResponse(
            answer="For your safety, I cannot process personal information such as PAN, Aadhaar, or account numbers.",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="pii_blocked",
        )

    # 3. Classify the query: small_talk → advisory → factual → out_of_scope
    q_type = classify_query(sanitized_query)
    logger.info("Query classification: %s", q_type)

    # 3a. Small talk — friendly response, no retrieval, no citation
    if q_type == "small_talk":
        response = handle_small_talk(sanitized_query)
        logger.info("Returning small-talk response")
        return response

    # 3b. Advisory or out-of-scope — refusal
    if q_type in ("advisory", "out_of_scope"):
        response = handle_refusal(q_type)
        logger.info("Returning refusal response for type '%s'", q_type)
        return response

    # 4. Normalize query via LLM to resolve aliases AND pronouns from history
    rewritten_query = rewrite_query(sanitized_query, history)

    # 5. Retrieve relevant context (factual) using the normalized query
    chunks = retrieve_relevant_context(rewritten_query)

    if not chunks:
        logger.info("No relevant chunks found above similarity threshold.")
        return ChatResponse(
            answer="I could not find that in my sources. Could you rephrase your question or specify which HDFC fund you're asking about?",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="factual",
        )

    # 6. Generate response using LLM (using the rewritten query so the context matches)
    raw_answer = generate_response(rewritten_query, chunks, history)

    # Handle case where generator returns fallback answer or empty response
    if not raw_answer or not raw_answer.strip() or raw_answer == "I don't have this information in my current sources.":
        logger.info("Generator returned fallback/empty response.")
        return ChatResponse(
            answer=raw_answer if raw_answer and raw_answer.strip() else "I could not find that in my sources.",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="factual",
        )

    # 7. Validate citations & post-process
    cleaned_answer, citation, footer = validate_citations(raw_answer, chunks)

    # 8. Build contextual follow-up chip
    # Only show a follow-up chip when a specific fund was identified in the answer
    follow_up = None
    scheme_name = citation.scheme_name
    if scheme_name and scheme_name not in ("AMFI India", "HDFC Mutual Fund"):
        # Make the chip specific — use the actual fund name
        # Strip "Direct Growth" suffix for cleaner display
        display_name = scheme_name.replace(" Direct Growth", "").replace(" Direct Plan Growth", "")
        follow_up = f"Tell me more about {display_name}"

    # 9. Save interaction to secondary memory (SQLite)
    add_message(session_id, "user", raw_query)
    add_message(session_id, "assistant", cleaned_answer)

    logger.info("Returning validated factual response for session %s.", session_id)
    return ChatResponse(
        answer=cleaned_answer,
        citation=citation,
        footer=footer,
        query_type="factual",
        follow_up=follow_up,
    )


from fastapi import BackgroundTasks
from app.ingestion.scheduler import scheduled_ingestion
import app.ingestion.scheduler as scheduler_module

@router.post("/admin/sync", status_code=202, tags=["Admin"])
async def manual_sync(background_tasks: BackgroundTasks):
    """
    Manually trigger the ingestion pipeline.
    Runs asynchronously as a background task so it doesn't block the API response.
    """
    logger.info("Manual ingestion sync triggered.")
    background_tasks.add_task(scheduled_ingestion)
    return {"message": "Knowledge base sync started in the background."}

@router.get("/admin/sync/status", tags=["Admin"])
async def sync_status():
    """Check if the knowledge base is currently syncing."""
    return {"is_syncing": scheduler_module.IS_SYNCING}


@router.post("/admin/reindex", status_code=202, tags=["Admin"])
async def reindex_from_data(background_tasks: BackgroundTasks):
    """
    Re-index the vector store from the pre-scraped chunks.json file.
    Does NOT require Playwright or scraping — works on Railway.
    """
    logger.info("Reindex from chunks.json triggered.")
    background_tasks.add_task(_reindex_task)
    return {"message": "Reindex from chunks.json started in the background."}


async def _reindex_task():
    """Background task to load chunks.json and index into the vector store."""
    import json
    from pathlib import Path
    from app.ingestion.chunker import Chunk
    from app.ingestion.vector_store import add_chunks, reset_store

    scheduler_module.IS_SYNCING = True
    try:
        # Try multiple possible locations for chunks.json
        possible_paths = [
            Path(__file__).resolve().parent.parent.parent / "data" / "chunks.json",  # /app/data/chunks.json (Docker)
            Path(__file__).resolve().parent.parent / "data" / "chunks.json",          # backend/data/ (local)
        ]

        chunks_file = None
        for p in possible_paths:
            if p.exists():
                chunks_file = p
                break

        if not chunks_file:
            logger.error("chunks.json not found in any expected location: %s", [str(p) for p in possible_paths])
            return

        logger.info("Loading chunks from %s", chunks_file)
        raw = json.loads(chunks_file.read_text(encoding="utf-8"))

        chunks = []
        for item in raw:
            chunks.append(Chunk(
                chunk_id=item["chunk_id"],
                text=item["text"],
                source_url=item["source_url"],
                scheme_name=item["scheme_name"],
                section=item["section"],
                scraped_at=item.get("scraped_at", ""),
            ))

        logger.info("Loaded %d chunks. Resetting vector store and re-indexing...", len(chunks))
        reset_store()
        add_chunks(chunks)
        logger.info("✓ Reindex complete. %d chunks indexed.", len(chunks))

    except Exception as e:
        logger.error("Reindex failed: %s", e, exc_info=True)
    finally:
        scheduler_module.IS_SYNCING = False
