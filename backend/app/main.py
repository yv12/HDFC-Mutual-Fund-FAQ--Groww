"""
FastAPI entry point for the Mutual Fund FAQ Assistant.

Run with:
    uvicorn app.main:app --reload
"""

import torch
import os
import sys
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

# Limit PyTorch to 1 thread to aggressively save memory on 512MB Render tier
torch.set_num_threads(1)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api.routes import router as api_router
from app.ingestion.scheduler import start_scheduler, stop_scheduler
from app.ingestion.embedder import get_embedding_model

import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



# ── Lifespan (startup / shutdown) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # ── Startup ───────────────────────────────────────────────────
    print("=" * 60)
    print("  Mutual Fund FAQ Assistant — Starting Up")
    print(f"  LLM Provider     : xAI Grok ({settings.llm_model})")
    print(f"  Embedding Model  : {settings.embedding_model} ({settings.embedding_dimensions}d, {settings.embedding_device})")
    print(f"  ChromaDB Path    : {settings.chroma_persist_dir}")
    print(f"  CORS Origins     : {settings.cors_origin_list}")
    print(f"  Rate Limit       : {settings.rate_limit_per_minute} req/min")
    print("=" * 60)

    # Pre-load embedding model at startup to avoid cold-load OOM spikes on first request
    print("  Pre-loading embedding model...")
    get_embedding_model()
    print("  ✓ Embedding model ready.")

    start_scheduler()
    yield
    # ── Shutdown ──────────────────────────────────────────────────
    stop_scheduler()
    print("Mutual Fund FAQ Assistant — Shutting Down")


# ── App Instance ─────────────────────────────────────────────────
app = FastAPI(
    title="Mutual Fund FAQ Assistant",
    description=(
        "A facts-only RAG-based FAQ assistant for HDFC mutual fund schemes. "
        "Provides concise, source-backed answers with strict citation integrity."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ── CORS Middleware ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ───────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")


# ── Health Endpoint (root-level, outside /api prefix) ────────────
# Defined BEFORE the static files mount so it isn't shadowed by the "/" catch-all.
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health-check endpoint.

    Returns 200 OK with basic system status information.
    Used by load balancers, monitoring tools, and smoke tests.
    """
    return {
        "status": "healthy",
        "service": "Mutual Fund FAQ Assistant",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "llm_provider": "xAI Grok",
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
            "chroma_collection": settings.chroma_collection_name,
        },
    }


# ── Static Files (Frontend) ─────────────────────────────────────
# Mounted LAST — the "/" catch-all must come after all explicit routes.
_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
