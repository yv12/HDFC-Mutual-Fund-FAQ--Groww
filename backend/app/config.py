"""
Centralized configuration module.

Loads all tunable parameters from environment variables / .env file
using pydantic-settings for type-safe validation and defaults.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the backend/ directory so .env lookup is path-independent
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings — loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM Provider (xAI / Grok) ─────────────────────────────────
    xai_api_key: str = ""
    xai_base_url: str = "https://api.x.ai/v1"

    # ── Model Configuration ───────────────────────────────────────
    llm_model: str = "grok-3-mini"

    # ── Embedding ─────────────────────────────────────────────────
    # Provider: "local" (sentence-transformers) or "api" (HuggingFace Inference API)
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dimensions: int = 1024
    embedding_device: str = "cpu"  # "cpu" or "cuda" (only used when provider="local")

    # ── HuggingFace Inference API (used when embedding_provider="api") ──
    hf_api_token: str = ""

    # ── Vector Store Provider ─────────────────────────────────────
    # Provider: "chroma" (local ChromaDB) or "qdrant" (Qdrant Cloud)
    vector_db_provider: str = "chroma"

    # ── ChromaDB (used when vector_db_provider="chroma") ──────────
    chroma_persist_dir: str = str(_BACKEND_DIR / "chroma_data")
    chroma_collection_name: str = "mutual_fund_faq"

    # ── Qdrant Cloud (used when vector_db_provider="qdrant") ──────
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection_name: str = "mutual_fund_faq"

    # ── Retrieval ─────────────────────────────────────────────────
    retrieval_top_k: int = 4
    similarity_threshold: float = 0.35

    # ── Chunking ──────────────────────────────────────────────────
    chunk_size: int = 250
    chunk_overlap: int = 30

    # ── API Server ────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:5500"

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_per_minute: int = 20

    # ── Scraping ──────────────────────────────────────────────────
    scrape_timeout_ms: int = 30000
    scrape_max_retries: int = 3

    # ── Scheduler ─────────────────────────────────────────────────
    enable_scheduler: bool = True  # Set to False on Railway (no cron allowed)

    # ── Computed helpers ──────────────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# ── Singleton instance ────────────────────────────────────────────
settings = Settings()
