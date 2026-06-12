# Architecture — Mutual Fund FAQ Assistant

> **Last Updated: 12-Jun-2026** — Embedding model downsize for Railway deployment.
> Switched from `BAAI/bge-large-en-v1.5` (1024d, ~1.3GB) to `BAAI/bge-small-en-v1.5` (384d, ~130MB)
> to resolve OOM (Out of Memory) kills on Railway's constrained runtime.
> See previous update: [Fix.txt](file:///d:/RAG%20Chatbot/Docs/Fix.txt) for the 11-Jun-2026 bug-fix change log.

## 1. System Overview

A lightweight **RAG (Retrieval-Augmented Generation)** system that ingests content from 5 pre-approved Groww URLs for HDFC mutual fund schemes, indexes them into a vector store, and serves facts-only answers through a minimal chat interface.

```mermaid
flowchart TB
    subgraph Offline["⚙️ Offline Pipeline (One-Time / Scheduled)"]
        S1["Web Scraper"] --> S2["Document Chunker"]
        S2 --> S3["Embedding Model"]
        S3 --> S4[("Vector Store")]
    end

    subgraph Online["⚡ Online Pipeline (Per Query)"]
        U["User Query"] --> QC["Query Classifier"]
        QC -->|Factual| QR["Query Rewriter (LLM)"]
        QR --> QE["Query Embedding"]
        QC -->|Advisory / Out-of-Scope| RF["Refusal Handler"]
        QE --> RT["Retriever"]
        RT <--> S4
        RT --> CTX["Context Builder"]
        CTX --> LLM["LLM + Facts-Only Prompt"]
        LLM --> CV["Citation Validator"]
        CV --> R["Response\n(≤ 3 sentences + citation)"]
        RF --> R
    end

    subgraph UI["🖥️ Frontend"]
        R --> Chat["Chat Interface"]
    end
```

---

## 1a. Post-Implementation Updates

### 1a.1 — Embedding Model Downsize (12-Jun-2026)

> [!IMPORTANT]
> The embedding model was switched from `BAAI/bge-large-en-v1.5` to `BAAI/bge-small-en-v1.5` to resolve
> **OOM (Out of Memory) kills** on Railway deployment.

#### What Was Found During Deployment
After deploying to Railway, every chat query that required embedding (e.g. *"What is the expense ratio of HDFC Mid Cap Fund?"*) caused the container process to be **killed by the OS** (OOM killer). The Railway deployment logs showed a repeating pattern:

```
Loading embedding model 'BAAI/bge-large-en-v1.5' on device 'cpu' ...
HTTP Request: HEAD .../model.safetensors "HTTP/1.1 302 Found"
Killed
```

The `bge-large-en-v1.5` model has **335M parameters** and requires **~1.3GB RAM** just for model weights. Combined with PyTorch, ChromaDB, Playwright/Chromium, and the FastAPI process, this exceeded Railway's container memory limit (~512MB–1GB on starter plans).

#### Changes Made

| # | Component | File | What Changed | Why |
|---|---|---|---|---|
| 1 | **Embedding Model** | `config.py` | Switched from `BAAI/bge-large-en-v1.5` (1024d, ~1.3GB) → `BAAI/bge-small-en-v1.5` (384d, ~130MB) | 10× smaller memory footprint. Same BGE model family, same training methodology, compatible with all existing pipeline logic. |
| 2 | **Startup Preload** | `main.py` | Added `get_embedding_model()` call during FastAPI startup lifespan | Ensures the model is loaded once into memory at boot, avoiding cold-load spikes when the first user request arrives. |
| 3 | **Docker Build Cache** | `Dockerfile` | Added `RUN python -c "...SentenceTransformer('BAAI/bge-small-en-v1.5')"` step | Pre-downloads the model during image build, eliminating runtime HuggingFace downloads and reducing startup latency. |
| 4 | **Nixpacks Build** | `nixpacks.toml` | Same model pre-download added to nixpacks install phase | Ensures Railway's nixpacks builder also caches the model in the image. |
| 5 | **Telemetry** | `Dockerfile`, `nixpacks.toml` | Set `ANONYMIZED_TELEMETRY=false` | Suppresses ChromaDB PostHog telemetry errors (`capture() takes 1 positional argument but 3 were given`) visible in Railway logs. |

> [!NOTE]
> Since the embedding dimensions changed from 1024 → 384, the existing ChromaDB vector store is incompatible.
> A manual sync (`POST /api/admin/sync`) must be triggered after the first deploy to re-index all chunks
> with the new 384-dimensional embeddings. The sync pipeline calls `reset_store()` automatically.

---

### 1a.2 — Pipeline Bug Fixes (11-Jun-2026)

> [!IMPORTANT]
> The following changes were made after real-world Q&A testing revealed that the bot was incorrectly returning
> *"I don't have this information"* for valid factual questions. Full details in [Fix.txt](file:///d:/RAG%20Chatbot/Docs/Fix.txt).

#### What Was Found During Testing
Six test questions were run against the deployed bot. Four of them failed — not because the data was missing from the database, but because bugs in the classifier, retriever, and configuration were silently blocking or discarding valid answers before the LLM ever saw them.

#### Changes Made

| # | Component | File | What Changed | Why |
|---|---|---|---|---|
| 1 | **Query Classifier** | `pipeline/query_classifier.py` | Removed overly broad advisory keywords (`best`, `better`, `invest`, `buy`, `sell`, `which fund`). Replaced with specific multi-word phrases (`should i invest`, `which is best`, `best fund`, `buy or sell`). Added 14 new factual keywords (`tell me`, `how long`, `withdraw`, `allocation`, `portfolio`, `scheme`, `factsheet`, etc.) | Single-word triggers were blocking perfectly factual questions. E.g. *"I want to invest — what is the expense ratio?"* was refused as advisory because the word `invest` appeared. |
| 2 | **Fund Alias Routing** | `pipeline/retriever.py` | Added popular Groww display-name aliases to `SCHEME_ROUTING_MAP`: `"top 100"` → Large Cap Fund, `"opportunities"` → Mid Cap Fund. Removed risky single-word keys (`mid`, `large`, `small`, `etf`) that could match unrelated words | Users type Groww display names like *"HDFC Top 100 Fund"* and *"HDFC Mid-Cap Opportunities Fund"*. The database stores official AMC names. Without the alias map, the retriever searched across all 5 funds randomly and returned nothing or the wrong fund. |
| 3 | **Similarity Threshold** | `config.py` | Lowered `similarity_threshold` from **0.5 → 0.35** | The `BAAI/bge-large-en-v1.5` model returns scores of 0.35–0.65 for genuinely relevant but naturally phrased queries. A threshold of 0.5 was discarding half of all valid search results before the LLM could see them. |
| 4 | **LLM System Prompt** | `pipeline/generator.py` | Softened Rule 5 to allow simple logical inference (e.g. *"30 days is within 1 year, so exit load applies"*). Updated Rule 7 to explicitly tell the LLM that *"Top 100"* = Large Cap Fund and *"Mid-Cap Opportunities"* = Mid Cap Fund. | The original strict prompt caused the LLM to refuse answering even when the answer was clearly derivable from the context. |

---

## 2. Component Architecture

### 2.1 Offline Pipeline — Corpus Ingestion

Runs once at setup (and optionally on a schedule to refresh data).

```mermaid
flowchart LR
    A["5 Groww URLs"] --> B["Web Scraper"]
    B --> C["Raw HTML"]
    C --> D["Content Extractor\n& Cleaner"]
    D --> E["Document Chunker"]
    E --> F["Text Chunks\n+ Metadata"]
    F --> G["Embedding Model"]
    G --> H[("Vector Store")]
```

| Component | Responsibility | Details |
|---|---|---|
| **Web Scraper** | Fetch raw HTML from the 5 pre-approved URLs | Handles dynamic content if Groww uses client-side rendering (headless browser or API-based) |
| **Content Extractor** | Strip HTML, extract structured data (expense ratio, exit load, fund manager, AUM, etc.) | Preserves source URL as metadata on every extracted block |
| **Document Chunker** | Split cleaned content into retrieval-friendly chunks | Chunk size: ~300–500 tokens with overlap; each chunk retains its source URL |
| **Embedding Model** | Convert text chunks into vector embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers (local, open-source, 384-dim). *Downsized from `bge-large` (1024d) on 12-Jun-2026 due to Railway OOM kills — see §1a.1.* |
| **Vector Store** | Store and index embeddings for fast similarity search | Options: ChromaDB (lightweight), Pinecone, FAISS, or Weaviate |

#### Chunk Metadata Schema

Each chunk stored in the vector store carries metadata to support citation integrity:

```json
{
  "chunk_id": "hdfc-midcap-003",
  "text": "The expense ratio of HDFC Mid Cap Fund Direct Growth is 0.74%...",
  "source_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
  "scheme_name": "HDFC Mid Cap Fund – Direct Growth",
  "section": "Fund Details",
  "scraped_at": "2026-06-02T00:00:00Z"
}
```

---

### 2.2 Online Pipeline — Query Processing

Handles each user query in real time.

```mermaid
sequenceDiagram
    actor User
    participant UI as Chat UI
    participant QC as Query Classifier
    participant QR as Query Rewriter
    participant RET as Retriever
    participant VS as Vector Store
    participant LLM as LLM Engine
    participant CV as Citation Validator

    User->>UI: Sends query
    UI->>QC: Forward query
    
    alt Advisory / Out-of-Scope
        QC-->>UI: Polite refusal + educational link
    else Factual Query
        QC->>QR: Pass classified query
        QR->>QR: Normalize aliases via LLM
        QR->>RET: Pass normalized query
        RET->>VS: Similarity search (top-k)
        VS-->>RET: Relevant chunks + metadata
        RET->>LLM: Query + retrieved context + system prompt
        LLM->>CV: Draft response
        CV->>CV: Validate URLs against chunk metadata
        CV-->>UI: Final response (≤ 3 sentences + citation + footer)
    end

    UI-->>User: Display response
```

| Component | Responsibility | Details |
|---|---|---|
| **Query Classifier** | Detect whether query is factual or advisory/out-of-scope | Keyword-based heuristic classification. Advisory check runs first using specific multi-word phrases only. Factual keyword list covers 30+ natural-language patterns. *(Updated 11-Jun-2026 — see Fix.txt)* |
| **Query Rewriter** | Normalize user query | Uses LLM to replace slang and aliases with official fund names before retrieval. |
| **Retriever** | Find the most relevant chunks for the user's question | Cosine similarity search with fund-alias routing. Retrieves top-k=4 chunks; applies `scheme_name` metadata filter when a fund keyword or alias is detected in the query. *(Updated 11-Jun-2026 — see Fix.txt)* |
| **LLM Engine** | Generate a concise, facts-only answer from retrieved context | xAI Grok-3-mini via OpenAI-compatible SDK; strict system prompt (≤ 3 sentences, no advice, no fabricated data, allows simple logical inference). *(Updated 11-Jun-2026 — see Fix.txt)* |
| **Citation Validator** | Ensure all URLs in the response exist verbatim in retrieved chunk metadata | **Zero-generation policy**: if URL not found in metadata → replace with text-only citation |
| **Refusal Handler** | Return polite refusal for advisory queries | Includes the reason for refusal + an educational link (AMFI/SEBI) |

---

### 2.3 Citation Validation Flow

A dedicated post-processing step that enforces the zero-hallucination link policy.

```mermaid
flowchart TD
    A["LLM Draft Response"] --> B{"Contains URLs?"}
    B -->|No| C["Attach source URL from\ntop-ranked chunk metadata"]
    B -->|Yes| D{"URL exists in\nchunk metadata?"}
    D -->|Yes| E["✅ Keep URL as-is"]
    D -->|No| F["🚫 Strip hallucinated URL"]
    F --> G["Replace with text-only citation\n(document name + section)"]
    C --> H["Append footer:\nLast updated from sources: date"]
    E --> H
    G --> H
    H --> I["Final Response"]
```

> [!IMPORTANT]
> The LLM must **never** generate, infer, or construct URLs. All hyperlinks in the final response are **extracted verbatim** from the `source_url` field in chunk metadata. If no verified URL is available, the system falls back to a **text-only citation** (scheme name + section title).

---

### 2.4 Refusal Handling Flow

```mermaid
flowchart LR
    A["User Query"] --> B{"Query Classifier"}
    B -->|"Investment advice\n(Should I invest?)"| C["Refusal Response"]
    B -->|"Fund comparison\n(Which is better?)"| C
    B -->|"Return prediction\n(What returns?)"| C
    C --> D["Polite message +\nFacts-only reminder"]
    D --> E["Attach educational link\n(AMFI / SEBI resource)"]
```

**Example refusal response:**
> *"I can only provide factual information about mutual fund schemes. For investment guidance, please consult a SEBI-registered advisor or visit [amfiindia.com](https://www.amfiindia.com)."*

---

## 3. Data Flow Summary

| Stage | Input | Output | Key Constraint |
|---|---|---|---|
| **Scraping** | 5 Groww URLs | Raw HTML | Only pre-approved URLs |
| **Extraction** | Raw HTML | Structured text + metadata | Source URL preserved per block |
| **Chunking** | Structured text | Chunks (~250 tokens, 30-token overlap) | Section-aware; each chunk is self-contained |
| **Embedding** | Text chunks | Vector embeddings (384-dim) | Deterministic, reproducible. *Downsized from 1024-dim on 12-Jun-2026.* |
| **Indexing** | Vectors + metadata | Vector store entries | Metadata includes `source_url`, `scraped_at` |
| **Retrieval** | User query vector | Top-4 chunks above similarity ≥ 0.35 | Cosine similarity with alias-aware fund routing *(threshold lowered 11-Jun-2026)* |
| **Generation** | Query + context | Draft response | ≤ 3 sentences, facts only, logical inference allowed *(prompt updated 11-Jun-2026)* |
| **Citation Check** | Draft response + metadata | Validated response | Zero-generation URL policy |

---

## 4. Frontend Architecture

A minimal, single-page chat interface.

```mermaid
flowchart TB
    subgraph ChatUI["Chat Interface"]
        H["Header\n+ Disclaimer Banner"]
        EX["Example Questions (×3)"]
        CW["Chat Window\n(Message History)"]
        IN["Input Box + Send Button"]
    end

    IN -->|User query| API["Backend API"]
    API -->|Response| CW
```

| Element | Description |
|---|---|
| **Disclaimer Banner** | Persistent: *"Facts-only. No investment advice."* |
| **Welcome Message** | Greets the user, explains the assistant's scope |
| **Example Questions** | 3 clickable sample queries to guide first-time users |
| **Chat Window** | Scrollable message history with user/assistant bubbles |
| **Input Box** | Text input with send button; no file uploads or attachments |

---

## 5. Technology Stack (Recommended)

| Layer | Technology | Notes |
|---|---|---|
| **Frontend** | HTML/CSS/JS | Minimal chat UI |
| **Backend / API** | Python (FastAPI) | Handles query processing, RAG orchestration |
| **Web Scraping** | BeautifulSoup + Playwright | Playwright for JS-heavy Groww pages |
| **Embedding Model** | `BAAI/bge-small-en-v1.5` (sentence-transformers) | Local, open-source, zero API cost. *Downsized from `bge-large` on 12-Jun-2026 to fit Railway's memory limits.* |
| **Vector Store** | ChromaDB | Lightweight, embedded, persistent |
| **LLM** | Local open-source model (Llama 3 / Qwen 2.5) via Ollama | Runs locally, zero API cost; system prompt enforces constraints |
| **Orchestration** | LangChain | Simplifies RAG pipeline wiring |

---

## 6. Security & Privacy Architecture

```mermaid
flowchart LR
    A["User Input"] --> B["PII Scanner"]
    B -->|PII Detected| C["Block & Warn User"]
    B -->|Clean| D["Query Classifier"]
    D --> E["RAG Pipeline"]
```

> [!CAUTION]
> The system must **never** collect, store, or process PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers. A PII scanner at the input layer should detect and block such data before it enters the pipeline.

| Guardrail | Implementation |
|---|---|
| **Input PII filtering** | Regex-based scanner for PAN, Aadhaar patterns, emails, phone numbers |
| **No persistent user data** | Chat history is session-only; no database storage of user queries |
| **Source-only URLs** | Citation validator prevents injection of arbitrary external links |
| **Content boundary enforcement** | System prompt + query classifier block advisory content |

---

## 7. Deployment View

```mermaid
flowchart TB
    subgraph Client
        Browser["User Browser"]
    end

    subgraph Server["Application Server"]
        FE["Frontend\n(Static Files)"]
        API["API Server\n(FastAPI)"]
        RAG["RAG Pipeline"]
    end

    subgraph Storage
        VS[("Vector Store\n(ChromaDB)")]
        CFG["Config & Prompts"]
    end

    Browser <-->|HTTP| FE
    Browser <-->|REST API| API
    API <--> RAG
    RAG <--> VS
    RAG <--> CFG
```

---

## 8. References

| Document | Description |
|---|---|
| [problemStatement.md](file:///d:/RAG%20Chatbot/Docs/problemStatement.md) | Full problem statement with scope, constraints, and deliverables |
| [context.md](file:///d:/RAG%20Chatbot/Docs/context.md) | Project context — what, why, corpus, guardrails, and success criteria |
| [implementation-plan.md](file:///d:/RAG%20Chatbot/Docs/implementation-plan.md) | Phased implementation plan with tasks, acceptance criteria, and test matrix |
| [Fix.txt](file:///d:/RAG%20Chatbot/Docs/Fix.txt) | Bug-fix log (11-Jun-2026) — before/after explanation for all 4 pipeline changes made after real-world Q&A testing |
