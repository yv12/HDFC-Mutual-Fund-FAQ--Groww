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
from app.pipeline.refusal_handler import handle_refusal
from app.security.pii_scanner import scan_pii
from app.security.sanitizer import sanitize_input
from app.security.rate_limiter import rate_limit_dependency

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
      (retrieve → generate → validate citation) OR refusal → respond
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

    # 2. Scan for PII (PAN, Aadhaar, Email, Phone, OTP, Bank Account)
    if scan_pii(sanitized_query):
        logger.warning("Query blocked by PII scanner.")
        return ChatResponse(
            answer="For your safety, I cannot process personal information such as PAN, Aadhaar, or account numbers.",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="pii_blocked",
        )

    # 3. Classify the query (factual vs. advisory vs. out_of_scope)
    q_type = classify_query(sanitized_query)
    logger.info("Query classification: %s", q_type)

    if q_type in ("advisory", "out_of_scope"):
        response = handle_refusal(q_type)
        logger.info("Returning refusal response for type '%s'", q_type)
        return response

    # 4. Normalize query via LLM to resolve aliases
    rewritten_query = rewrite_query(sanitized_query)

    # 5. Retrieve relevant context (factual) using the normalized query
    chunks = retrieve_relevant_context(rewritten_query)

    if not chunks:
        logger.info("No relevant chunks found above similarity threshold.")
        return ChatResponse(
            answer="I don't have this information in my current sources.",
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="factual",
        )

    # 6. Generate response using LLM (using the rewritten query so the context matches)
    raw_answer = generate_response(rewritten_query, chunks)

    # Handle case where generator returns fallback answer
    if raw_answer == "I don't have this information in my current sources.":
        logger.info("Generator returned fallback/no info response.")
        return ChatResponse(
            answer=raw_answer,
            citation=CitationInfo(),
            footer="HDFC Mutual Fund FAQ Assistant",
            query_type="factual",
        )

    # 6. Validate citations & post-process
    cleaned_answer, citation, footer = validate_citations(raw_answer, chunks)

    logger.info("Returning validated factual response.")
    return ChatResponse(
        answer=cleaned_answer,
        citation=citation,
        footer=footer,
        query_type="factual",
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


