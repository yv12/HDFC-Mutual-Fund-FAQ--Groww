# Fundpedia AI — Fact Sheet (HDFC Mutual Fund RAG Assistant)

---

## 1. Architecture

### System Components & Responsibilities
* **Frontend** ([frontend/index.html](file:///d:/RAG%20Chatbot/frontend/index.html), [frontend/index.js](file:///d:/RAG%20Chatbot/frontend/index.js), [frontend/index.css](file:///d:/RAG%20Chatbot/frontend/index.css)):
  * Web-based user interface.
  * Sends questions to backend via HTTP POST `fetch`.
  * Manages session UUIDs and stores conversation history in browser `localStorage`.
  * Displays sync status pill, progress indicators, interactive clarification options, contextual follow-up suggestions, and verified source citations.
* **Backend** ([backend/app/main.py](file:///d:/RAG%20Chatbot/backend/app/main.py), [backend/app/api/routes.py](file:///d:/RAG%20Chatbot/backend/app/api/routes.py)):
  * FastAPI REST API server running on Uvicorn/Gunicorn.
  * Enforces rate limiting, prompt sanitization, PII filtering, and sync-lock handling.
  * Coordinates multi-stage RAG query processing, secondary memory logging in SQLite ([backend/data/chat_history.db](file:///d:/RAG%20Chatbot/backend/data/chat_history.db)), and admin endpoints.
* **Vector Database** ([backend/app/ingestion/vector_store.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/vector_store.py)):
  * Stores 1024-dimensional dense vectors and chunk metadata.
  * Dual-mode design: **Qdrant Cloud** (production) or local **ChromaDB** (development).
  * Performs cosine similarity search with fund-level metadata filtering.
* **Embedding Service** ([backend/app/ingestion/embedder.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/embedder.py)):
  * Generates 1024-dimensional dense vector embeddings using `BAAI/bge-large-en-v1.5`.
  * Automatically prepends the BGE query prefix (`"Represent this sentence for searching relevant passages: "`).
  * Provider modes: **Cloudflare Workers AI** (production `.env`), **HuggingFace Serverless Inference API**, or local `sentence-transformers`.
* **LLM Engine** ([backend/app/pipeline/generator.py](file:///d:/RAG%20Chatbot/backend/app/pipeline/generator.py), [backend/app/pipeline/query_rewriter.py](file:///d:/RAG%20Chatbot/backend/app/pipeline/query_rewriter.py)):
  * OpenAI SDK client connecting to an OpenAI-compatible endpoint.
  * Query Rewriter resolves pronouns and normalizes aliases using conversation history.
  * Generator crafts concise (≤ 3 sentences), facts-only answers strictly from retrieved context passages.
* **Data Ingestion** ([backend/app/scraper/scraper.py](file:///d:/RAG%20Chatbot/backend/app/scraper/scraper.py), [backend/app/ingestion/chunker.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/chunker.py), [backend/scripts/ingest.py](file:///d:/RAG%20Chatbot/backend/scripts/ingest.py)):
  * Automated pipeline fetching data from 5 pre-approved Groww URLs using Playwright headless Chromium.
  * Extracts structured mutual fund data from Next.js `<script id="__NEXT_DATA__">` (with DOM fallbacks).
  * Splits content into section-aware chunks, creates embeddings, and updates JSON caches and the vector database.
* **Scheduler** ([backend/app/ingestion/scheduler.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/scheduler.py), [.github/workflows/daily-ingest.yml](file:///d:/RAG%20Chatbot/.github/workflows/daily-ingest.yml)):
  * APScheduler `AsyncIOScheduler` configured for a daily cron at 09:15 AM IST (enabled locally, disabled on Railway).
  * GitHub Actions workflow running on a daily cron schedule at 04:30 UTC (10:00 AM IST).

### Step-by-Step Flow: User Question to Screen Display
1. **User Submission**: User submits a query or clicks an interactive chip. Frontend appends the user bubble and shows an animated typing indicator.
2. **Sync Lock Verification**: If `IS_SYNCING` is `True`, the backend returns *"The knowledge base is currently being updated. Please try again in a few minutes."*
3. **Rate Limiting**: [rate_limit_dependency](file:///d:/RAG%20Chatbot/backend/app/security/rate_limiter.py#L59-L82) verifies the client IP has not exceeded 20 requests in the past 60 seconds (HTTP 429 if exceeded).
4. **Input Sanitization**: [sanitize_input](file:///d:/RAG%20Chatbot/backend/app/security/sanitizer.py#L24-L54) truncates query to 500 characters and strips prompt injection phrases.
5. **Session History Retrieval**: [get_session_history](file:///d:/RAG%20Chatbot/backend/app/api/history.py#L38-L58) loads the last 10 messages from SQLite for context resolution.
6. **PII Scanning**: [scan_pii](file:///d:/RAG%20Chatbot/backend/app/security/pii_scanner.py#L29-L72) scans for PAN, Aadhaar, email, phone, OTP, or bank accounts; blocks request immediately if found (`query_type="pii_blocked"`).
7. **Query Classification**: [classify_query](file:///d:/RAG%20Chatbot/backend/app/pipeline/query_classifier.py#L114-L157) evaluates regex rules:
   * `small_talk` returns friendly greeting/meta text without vector retrieval.
   * `advisory` or `out_of_scope` returns refusal text (with AMFI India guidance link).
8. **Disambiguation Check**: [detect_ambiguous_scheme_query](file:///d:/RAG%20Chatbot/backend/app/pipeline/query_rewriter.py#L89-L129) checks if an attribute (e.g. "exit load") or pronoun is asked without a fund name and none exists in history. If ambiguous, returns a clarification prompt with 5 fund selection chips (`query_type="clarification"`).
9. **Query Normalization**: [rewrite_query](file:///d:/RAG%20Chatbot/backend/app/pipeline/query_rewriter.py#L149-L223) uses LLM (`temperature=0.0`, `max_tokens=100`) to resolve pronouns and expand nicknames to official scheme names.
10. **Vector Retrieval**: [retrieve_relevant_context](file:///d:/RAG%20Chatbot/backend/app/pipeline/retriever.py#L50-L104) runs cosine similarity search for top-4 chunks, applying a scheme metadata filter if a fund name is present, and discards chunks with similarity below `0.35`. If none remain, returns fallback source guidance.
11. **LLM Generation**: [generate_response](file:///d:/RAG%20Chatbot/backend/app/pipeline/generator.py#L19-L100) formats context chunks into labeled blocks and calls LLM (`temperature=0.0`, `max_tokens=300`) with strict facts-only guidelines (≤ 3 sentences, no speculation).
12. **Citation Validation**: [validate_citations](file:///d:/RAG%20Chatbot/backend/app/pipeline/citation_validator.py#L22-L108) verifies URLs against chunk metadata; unverified URLs are replaced with plain text `[Scheme - Section]`.
13. **Session Persistence**: User question and assistant answer are saved to SQLite table `messages`.
14. **Frontend Rendering**: Frontend removes typing shimmer, renders Markdown, appends verified source URL link with timestamp, and displays follow-up chips.

### Step-by-Step Flow: Data Synchronization
1. **Trigger**: Triggered via CLI (`python -m scripts.ingest`), admin endpoints (`/api/admin/sync` or `/api/admin/reindex`), or GitHub Actions workflow (`daily-ingest.yml`).
2. **Lock State**: Sets `IS_SYNCING = True` to reject/queue concurrent user queries.
3. **Scraping**: Playwright launches headless Chromium, navigates to the 5 Groww URLs (30s timeout, up to 3 retries with exponential backoff).
4. **Extraction**: Reads Next.js hydration state from `<script id="__NEXT_DATA__">` (DOM extraction fallback).
5. **Section Construction**: Formats raw attributes into distinct self-contained sections: "Overview", "Fund Details", "Exit Load", "Fund Managers", "Returns", "About", and "Investment Objective".
6. **Chunking**: Splits section text into chunks using sentence-level boundaries with `chunk_size=250` tokens and `chunk_overlap=30` tokens.
7. **Local Persistence**: Writes data to [scraped_funds.json](file:///d:/RAG%20Chatbot/backend/data/scraped_funds.json), [chunks.json](file:///d:/RAG%20Chatbot/backend/data/chunks.json), and [chunks_preview.md](file:///d:/RAG%20Chatbot/backend/data/chunks_preview.md).
8. **Vector Indexing**: Resets the target collection, generates 1024-dim vectors via the configured embedding provider, and uploads points to Qdrant Cloud / ChromaDB.
9. **Unlock**: Resets `IS_SYNCING = False`.

---

## 2. Tech Stack and Provider for Each Component

* **Frontend**:
  * Framework: Vanilla HTML5, CSS3, JavaScript (no framework, no build system).
  * Hosting Provider: **Vercel** (`https://hdfc-mutual-fund-faq-groww.vercel.app`) and served statically by FastAPI (`/`) on Railway.
* **Backend**:
  * Language: Python 3.12 (Dockerfile & GitHub Actions) / Python 3.10+ (locally).
  * Framework: FastAPI (Uvicorn / Gunicorn).
  * Hosting Provider and Plan: **Railway Free Plan / Hobby Tier** (512 MB RAM, 512 MB disk, 1 vCPU; production: `https://hdfc-mutual-fund-faq-groww-production.up.railway.app`).
* **Vector Database**:
  * Product Name: **Qdrant Cloud** (production) and **ChromaDB** (local development).
  * Where it Runs:
    * Qdrant: Remote cloud cluster in AWS `sa-east-1` (`https://e4399030-2e5a-4fd1-bf4f-9810ff24fab1.sa-east-1-0.aws.cloud.qdrant.io`).
    * ChromaDB: Local disk at `backend/chroma_data`.
  * Collection Name: `mutual_fund_faq` (isolated test collection: `test_mutual_fund_faq`).
  * Distance Metric: Cosine similarity (`Distance.COSINE` in Qdrant, `{"hnsw:space": "cosine"}` in ChromaDB).
* **Embeddings**:
  * Exact Model Name: `BAAI/bge-large-en-v1.5`.
  * Provider:
    * Production `.env`: **Cloudflare Workers AI** (`@cf/baai/bge-large-en-v1.5`).
    * Configured options: **HuggingFace Serverless Inference API** and local `sentence-transformers`.
  * Vector Size: 1024 dimensions.
* **LLM**:
  * Exact Provider & Model Name:
    * Production `.env`: **Groq** (`https://api.groq.com/openai/v1`), model `qwen/qwen3.8-27b`.
    * Default in `config.py`: **xAI** (`https://api.x.ai/v1`), model `grok-3-mini`.
    * Documented in deployment plan: `openai/gpt-oss-20b` via Groq.
  * Temperature: `0.0`.
  * Max Tokens: `300` (generator), `100` (query rewriter).
  * System Prompt Summary: Strict facts-only assistant: Answer only using context; maximum 3 sentences; zero advice/opinions; never invent URLs; if info is missing say *"I don't have this information in my current sources."* (allows simple inferences); no manual source footers; never calculate or project future returns from past performance.
* **Data Source**:
  * Exact Websites / Files: Exactly 5 pre-approved URLs on Groww (`groww.in`):
    1. `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth`
    2. `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth`
    3. `https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth`
    4. `https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth`
    5. `https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth`
    * Local pre-scraped files: [scraped_funds.json](file:///d:/RAG%20Chatbot/backend/data/scraped_funds.json), [chunks.json](file:///d:/RAG%20Chatbot/backend/data/chunks.json), [chunks_preview.md](file:///d:/RAG%20Chatbot/backend/data/chunks_preview.md).
  * Fetch Method: Playwright headless Chromium extracting Next.js `<script id="__NEXT_DATA__">` with DOM fallback.
* **Anything Else**:
  * Scheduler: APScheduler `AsyncIOScheduler` (local 09:15 AM IST cron) & GitHub Actions cron (04:30 UTC / 10:00 AM IST).
  * Cache: In-memory module singletons; browser `localStorage` (`lumina_sessions`).
  * Logging: Python standard library `logging`.
  * Analytics: not found.

---

## 3. Data

* **Names of the 5 Schemes**:
  1. HDFC Mid Cap Fund Direct Growth
  2. HDFC Large Cap Fund Direct Growth
  3. HDFC Small Cap Fund Direct Growth
  4. HDFC Gold ETF Fund of Fund Direct Plan Growth
  5. HDFC Defence Fund Direct Growth
* **Number of Documents and Chunks**:
  * Documents: 5 fund documents (one per scheme).
  * Chunks: Exactly 35 chunks.
* **Chunk Size, Overlap, and Saved Metadata**:
  * Chunk Size: `250` tokens.
  * Chunk Overlap: `30` tokens.
  * Metadata Saved per Chunk: `chunk_id`, `text`, `source_url`, `scheme_name`, `section`, `scraped_at`.
* **Passages Retrieved per Question (Top k)**:
  * Top k = `4` (filtered by similarity threshold `0.35`).
* **Date of Last Data Refresh**:
  * `20-Jun-2026` (Scraped between `2026-06-20T17:09:24Z` and `2026-06-20T17:09:40Z`; NAV dates in data: `19-Jun-2026`).

---

## 4. Guardrails

* **Query Classifier**:
  * Rules, Model, or Both?: **Rules only** (Regex heuristics in [query_classifier.py](file:///d:/RAG%20Chatbot/backend/app/pipeline/query_classifier.py)).
  * Categories and 3 Example Questions:
    1. `small_talk`:
       * *"hello"*
       * *"What can you do?"*
       * *"Thank you so much!"*
    2. `advisory`:
       * *"Should I invest in HDFC Mid Cap Fund?"*
       * *"Which is better — mid cap or small cap?"*
       * *"Calculate returns for 10 years SIP"*
    3. `factual`:
       * *"What is the expense ratio of HDFC Mid Cap Fund?"*
       * *"Who is the fund manager of HDFC Small Cap?"*
       * *"What is the exit load for HDFC Large Cap Fund?"*
    4. `out_of_scope`:
       * *"What is the weather today in Mumbai?"*
       * *"Who won the cricket match yesterday?"*
       * *"tell me a joke"*
* **PII Scanner**:
  * Items Blocked:
    * PAN card numbers (`\b[A-Z]{5}[0-9]{4}[A-Z]\b`)
    * Aadhaar card numbers (`\b[0-9]{4}\s?[0-9]{4}\s?[0-9]{4}\b`)
    * Indian phone numbers (`(\+91[\-\s]?)?[6-9]\d{9}`)
    * Email addresses (`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
    * OTP codes (4–6 digits when context contains `"otp"`)
    * Bank account numbers (9–18 digits when context contains bank keywords)
  * Exact Message Shown:
    `"For your safety, I cannot process personal information such as PAN, Aadhaar, or account numbers."`
* **Citation Validator**:
  * What it Checks: Scans LLM output for URLs and verifies that each URL matches retrieved chunk metadata verbatim.
  * What Happens on Failure: Strips unverified URLs and replaces them with a text citation `[<scheme_name> - <section>]`. Attaches source citation metadata from the top-ranked chunk.
* **Response When Finding No Source**:
  * When no chunks exceed the similarity threshold:
    `"I could not find that in my sources. Could you rephrase your question or specify which HDFC fund you're asking about?"`
  * When LLM generation returns empty or fallback:
    `"I could not find that in my sources."` (or `"I don't have this information in my current sources."`)
* **Behavior When Query Lacks Fund Name or is Unclear**:
  * If a fund attribute or pronoun is requested without naming a scheme and none is present in recent history:
    Categorized as `clarification`. Returns:
    `"Which HDFC scheme are you asking about? Please select one below:"`
    with 5 attribute-tailored chips (e.g. `["Expense ratio of HDFC Mid Cap Fund", ...]`).
  * If the question has no fund name and fails similarity retrieval:
    Returns the no-source response with 5 default scheme buttons.
  * If the query is completely empty after sanitization:
    Returns `"Please ask a valid factual question regarding HDFC Mutual Fund schemes."` (`query_type="out_of_scope"`).

---

## 5. API

* `GET /health` — Health check endpoint returning service status (200 OK), timestamp, and active configuration.
* `POST /api/chat` — Processes user questions through RAG guardrail pipeline and returns structured JSON answers.
* `POST /api/admin/sync` — Asynchronously triggers web scraping and vector ingestion pipeline in the background (HTTP 202).
* `GET /api/admin/sync/status` — Checks whether knowledge base data synchronization is active (`{"is_syncing": boolean}`).
* `POST /api/admin/reindex` — Re-indexes vector store directly from local `chunks.json` without web scraping (HTTP 202).
* `GET /` — Serves static frontend files (`index.html`, `index.css`, `index.js`).

---

## 6. Performance and Limits

* **Typical Response Time**:
  * Deterministic Query Classification: `< 1ms` ([Docs/UAT_Edge_Case_Testing.md](file:///d:/RAG%20Chatbot/Docs/UAT_Edge_Case_Testing.md#L157)).
  * Vector Retrieval Target Latency: `< 500ms` ([Docs/implementation-plan.md](file:///d:/RAG%20Chatbot/Docs/implementation-plan.md#L217)).
  * Cold Start Latency: `~5-10s` on Railway container spin-up, plus `~1-2s` for HuggingFace cold calls ([Docs/deployment-plan.md](file:///d:/RAG%20Chatbot/Docs/deployment-plan.md#L314)).
  * End-to-end full chat turn stopwatch measurement: not found.
* **Free Tier Limits and Costs**:
  * **Railway**: 512 MB RAM, 512 MB disk, 1 vCPU; container sleeps after inactivity ($0 cost).
  * **Qdrant Cloud**: 1 GB RAM, 4 GB disk, 1 cluster; cluster deleted after 4 weeks without traffic ($0 cost).
  * **Groq**: ~14,400 tokens/minute rate limit ($0 cost).
  * **HuggingFace Inference API**: Free Serverless Inference rate limits apply ($0 cost).
  * **Cloudflare Workers AI**: Free tier for `@cf/baai/bge-large-en-v1.5` embeddings ($0 cost).
  * **Vercel**: Free hobby tier for static frontend hosting ($0 cost).
  * **GitHub Actions**: 2,000 free runner minutes/month ($0 cost).
* **Known Weak Spots and Bugs**:
  1. **Scraper reliance on Groww markup**: Reliant on Next.js `<script id="__NEXT_DATA__">` and CSS selectors; changes to Groww layout will break scraping ([QandA.txt](file:///d:/RAG%20Chatbot/QandA.txt) Q3).
  2. **Missing portfolio breakdown data**: Scraper does not fetch equity/debt/cash allocation or stock holdings; asset allocation queries return *"I don't have this information"* ([Docs/Fix.txt](file:///d:/RAG%20Chatbot/Docs/Fix.txt) Q6).
  3. **Railway ephemeral disk**: SQLite chat history resets on redeploy; Playwright cannot run on Railway due to the 512 MB memory limit.
  4. **Fixed k=4 coverage ceiling**: Multi-part questions requiring more than 4 sections will drop remaining sections due to the top-4 retrieval cutoff ([QandA.txt](file:///d:/RAG%20Chatbot/QandA.txt) Q5 & Q6).
  5. **In-memory rate limiting**: Rate limits are stored in RAM; resets on container restart and is not shared across multi-worker instances.

---

## 7. Testing

* **Automated Pytest Suite** ([backend/tests/](file:///d:/RAG%20Chatbot/backend/tests)):
  * 10 test modules: `test_chunker.py`, `test_citation.py`, `test_classifier.py`, `test_config.py`, `test_disambiguation.py`, `test_embedder.py`, `test_pii.py`, `test_pipeline.py`, `test_scraper.py`, `test_vector_store.py`.
  * Pass count: **78 passed out of 78 tests** (100% passing in 44.46 seconds).
* **UAT & Edge-Case Evaluation Suite** ([Docs/UAT_Edge_Case_Testing.md](file:///d:/RAG%20Chatbot/Docs/UAT_Edge_Case_Testing.md)):
  * 41 test cases across 6 categories (Small Talk, Projections, Suitability/Timing, Benchmark Comparisons, Factual Attributes, Complex/Hinglish).
  * Pass count: **41 passed out of 41 test cases** (100% pass rate, 0 failures, 0 blank responses, 0 advisory leakages).
* **Historical Bug Fix Validation Suite** ([Docs/Fix.txt](file:///d:/RAG%20Chatbot/Docs/Fix.txt)):
  * 6 benchmark queries tested to resolve false refusals (Mid-Cap Opportunities alias, Small Cap min SIP, Top 100 30-day exit load inference, Small Cap riskometer, Mid-Cap Opportunities benchmark index, Top 100 asset allocation).
