# Mutual Fund FAQ Assistant

> **Facts-only. No investment advice.**

A RAG-based FAQ assistant that answers factual questions about HDFC mutual fund schemes using verified data from Groww.

---

## Overview

This assistant retrieves information exclusively from **5 pre-approved Groww URLs** for HDFC mutual fund schemes and provides concise, source-backed answers. It strictly avoids investment advice, opinions, or recommendations.

### Selected AMC & Schemes

| # | Scheme | Source |
|---|---|---|
| 1 | HDFC Mid Cap Fund – Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| 2 | HDFC Large Cap Fund – Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |
| 3 | HDFC Small Cap Fund – Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth) |
| 4 | HDFC Gold ETF Fund of Fund – Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth) |
| 5 | HDFC Defence Fund – Direct Growth | [Groww](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth) |

---

## Architecture (Dual-Mode RAG Approach)

> **Updated 20-Jun-2026:** Migrated to a **Dual-Mode Architecture** to support free cloud deployment.

### Before vs After (Railway Free Plan Migration)

When initially built for local development, the application used heavy local Machine Learning libraries. To deploy to Railway's Free Plan (Max 512 MB RAM, 512 MB disk), the heavy components were offloaded to free cloud APIs.

| Component | Before (Local Mode) | After (Cloud / Production Mode) | Why? |
|---|---|---|---|
| **Embeddings** | Local `sentence-transformers` (`BAAI/bge-large-en-v1.5`) | **HuggingFace Inference API** | Saved ~1.3 GB RAM. Both modes produce identical vectors. |
| **Vector Database**| Local `ChromaDB` (on disk) | **Qdrant Cloud** (Free Tier) | Saved ~543 MB persistent disk space. |
| **Scheduler** | `APScheduler` (Background Cron) | **Disabled** on Railway | Railway prohibits background cron jobs. |
| **Scraper** | Runs via Playwright in the app | **Runs Locally** before deploy | Headless Chrome exceeds Railway's 512 MB RAM limit. |

### Pipeline Flow
```text
User Query → PII Scanner → Query Classifier → Retriever (Qdrant/Chroma) → LLM Generator → Citation Validator → Response
```

- **Offline/Scheduled Pipeline**: Scrape Groww URLs → Extract → Chunk → Embed (HF API or Local) → Store in Vector DB.
- **Online Pipeline**: Classify query → Retrieve top-k chunks → Generate facts-only answer (Groq LLM) → Validate citations.
- **Zero-hallucination link policy**: All URLs in responses come verbatim from chunk metadata — the LLM never generates URLs.
- **Frontend UI**: A modern, responsive chat interface served directly by FastAPI.

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- An xAI API key (for Grok LLM generation via OpenAI-compatible SDK)

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd "RAG Chatbot"

# 2. Create and activate virtual environment
cd backend
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
copy .env.example .env
# Edit .env and add your OpenAI API key
```

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `EMBEDDING_PROVIDER` | `local` (sentence-transformers) or `api` (HuggingFace API) | `local` |
| `VECTOR_DB_PROVIDER` | `chroma` (Local disk) or `qdrant` (Qdrant Cloud) | `chroma` |
| `HF_API_TOKEN` | HuggingFace token (Required if `EMBEDDING_PROVIDER=api`) | - |
| `QDRANT_URL` | Qdrant cluster endpoint (Required if `VECTOR_DB_PROVIDER=qdrant`) | - |
| `QDRANT_API_KEY` | Qdrant API key (Required if `VECTOR_DB_PROVIDER=qdrant`) | - |
| `XAI_API_KEY` | Your Groq API key (using OpenAI compatible SDK) | *(required)* |
| `XAI_BASE_URL` | The Groq endpoint | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | LLM model name | `llama-3.1-8b-instant` |
| `ENABLE_SCHEDULER` | Set to `false` in production if background cron jobs are disabled | `true` |

### Running the Ingestion Script

```bash
# Scrape, chunk, embed, and index all mutual fund data
python -m scripts.ingest
```

### Starting the Server

```bash
# Start the FastAPI server with hot reload
uvicorn app.main:app --reload --port 8000
```

The API and Frontend UI will be available at `http://localhost:8000`. Visit `/docs` for the interactive Swagger UI.

---

## Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Ask a Question

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the expense ratio of HDFC Mid Cap Fund?"}'
```

### Web UI
Open your browser and navigate to `http://localhost:8000` to interact with the premium chat interface. You can also trigger knowledge base syncs from the Admin Controls panel in the UI.

### Example Questions

- *"What is the expense ratio of HDFC Mid Cap Fund?"*
- *"Who is the fund manager of HDFC Small Cap Fund?"*
- *"What is the exit load for HDFC Large Cap Fund?"*

---

## Disclaimer

> **This assistant provides factual information only. It does NOT provide investment advice, recommendations, or opinions. For investment guidance, consult a SEBI-registered advisor.**

---

## Known Limitations

- Data is sourced from Groww pages at scrape time — may become stale if not refreshed
- Only covers the 5 listed HDFC schemes; other AMCs or schemes are out of scope
- Cannot process images or PDFs embedded on Groww pages
- Responses are limited to 3 sentences for conciseness
- Does not support multi-turn conversations (each query is independent)

---

## License

This project is for educational and demonstration purposes only.
