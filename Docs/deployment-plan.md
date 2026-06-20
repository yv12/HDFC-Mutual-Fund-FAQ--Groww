# Deployment Plan — Mutual Fund FAQ Assistant

> **Created: 20-Jun-2026**
> **Target Platform:** Railway Free Plan (0 cost)
> **Architecture:** Dual-Mode Cloud API (HuggingFace Inference API + Qdrant Cloud + Groq)

---

## Overview

This document is the definitive step-by-step guide to deploy the Mutual Fund FAQ Assistant to Railway's free tier. Read it fully before starting — the order matters.

### What Is Already Done (Pre-requisites Completed)

The following was done before deployment and does NOT need to be repeated:

| # | What | Status |
|---|---|---|
| 1 | Migrated embedding to HuggingFace Inference API (dual-mode) | ✅ Done |
| 2 | Migrated vector store to Qdrant Cloud (dual-mode) | ✅ Done |
| 3 | Created slim `requirements.railway.txt` (~200 MB vs ~3 GB) | ✅ Done |
| 4 | Created multi-stage `Dockerfile` for Railway | ✅ Done |
| 5 | Created `railway.json` deployment manifest | ✅ Done |
| 6 | Created `.dockerignore` to exclude 543 MB of ChromaDB data | ✅ Done |
| 7 | Got HuggingFace free API token | ✅ Done |
| 8 | Created Qdrant Cloud free cluster (AWS sa-east-1) | ✅ Done |
| 9 | Ran local ingestion — 35 chunks uploaded to Qdrant Cloud | ✅ Done |

---

## Free Services Used

> [!NOTE]
> Every single service below is 100% free. No credit card is required for any of them.

| Service | Purpose | Free Limit | Sign Up |
|---|---|---|---|
| **Railway** | Host the FastAPI app | 512 MB RAM, 512 MB disk, 1 vCPU | [railway.app](https://railway.app) |
| **Qdrant Cloud** | Vector database (35 chunks) | 1 GB RAM, 4 GB disk, 1 cluster | [cloud.qdrant.io](https://cloud.qdrant.io) |
| **HuggingFace** | Generate query embeddings at runtime | Free Serverless Inference | [huggingface.co](https://huggingface.co) |
| **Groq** | LLM (llama-3.1-8b-instant) | ~14,400 tokens/min free | [console.groq.com](https://console.groq.com) |
| **GitHub** | Source code hosting (needed by Railway) | Unlimited public repos | [github.com](https://github.com) |

---

## Step 1 — Verify the `.env` Is NOT Committed to Git

> [!CAUTION]
> The `.env` file contains your API keys. It must NEVER be committed to Git.
> The `.gitignore` file already has `.env` listed, but always double-check before pushing.

Run this to verify `.env` is properly ignored:

```powershell
cd "d:\RAG Chatbot"
git check-ignore -v backend/.env
```

**Expected output:** `backend/.gitignore:13:.env    backend/.env`

If you see no output, the file is being tracked. Fix it with:
```powershell
git rm --cached backend/.env
```

---

## Step 2 — Verify the Qdrant Data Is Live

Before deploying, confirm the 35 chunks were uploaded successfully to Qdrant Cloud.

Open a browser and paste this URL (replacing the API key):

```
https://2522b98e-1be7-4ced-be02-853b0be095b4.sa-east-1-0.aws.cloud.qdrant.io:6333/collections/mutual_fund_faq
```

Add a header `api-key: <your_qdrant_api_key>` — or simply run this command in PowerShell:

```powershell
cd "d:\RAG Chatbot\backend"
$env:EMBEDDING_PROVIDER="api"
$env:VECTOR_DB_PROVIDER="qdrant"
.\venv\Scripts\python.exe -c "
from app.ingestion.vector_store import _get_qdrant_client
from app.config import settings
client = _get_qdrant_client()
info = client.get_collection(settings.qdrant_collection_name)
print(f'Points in Qdrant: {info.points_count}')
print(f'Expected: 35')
"
```

**Expected output:** `Points in Qdrant: 35`

---

## Step 3 — Push Code to GitHub

Railway deploys directly from a GitHub repository. You need to push your code before Railway can build it.

### 3.1 — Initialize Git (if not already done)

```powershell
cd "d:\RAG Chatbot"
git init
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

### 3.2 — Stage and Commit

```powershell
git add .
git status   # Review what will be committed — .env should NOT appear
git commit -m "feat: Railway free-plan deployment setup

- Dual-mode embedder (local sentence-transformers / HF Inference API)
- Dual-mode vector store (ChromaDB / Qdrant Cloud)
- Conditional scheduler (disabled on Railway)
- requirements.railway.txt (slim, ~200MB)
- Multi-stage Dockerfile
- railway.json deployment manifest
- .dockerignore to exclude chroma_data
- Qdrant Cloud seeded with 35 mutual fund chunks"
```

### 3.3 — Push to GitHub

```powershell
git push -u origin main
```

---

## Step 4 — Create a Railway Account

1. Go to [railway.app](https://railway.app) and click **"Start a New Project"**
2. Sign in with **GitHub** (this is the easiest way — Railway will be able to read your repositories)
3. Railway's free plan is activated automatically — no credit card needed

---

## Step 5 — Create the Railway Project

1. On the Railway dashboard, click **"New Project"**
2. Click **"Deploy from GitHub repo"**
3. Find and select your RAG Chatbot repository
4. Railway will detect the `railway.json` in the root and start the build process automatically

> [!IMPORTANT]
> The `railway.json` tells Railway to build from `backend/Dockerfile` using the project root as the build context. This is why the Dockerfile references paths like `backend/app/` and `frontend/` — they are relative to the project root, not to the `backend/` folder.

---

## Step 6 — Set Environment Variables in Railway

> [!CAUTION]
> This is the most critical step. If any variable is missing or wrong, the app will crash silently on startup. Copy each one carefully.

In Railway, click on your deployed service → **"Variables"** tab → **"Add Variable"** for each one below:

### Required Variables (Production Mode)

| Variable | Value | Why |
|---|---|---|
| `EMBEDDING_PROVIDER` | `api` | Tells the app to use HuggingFace API instead of loading the 1.3GB local model |
| `VECTOR_DB_PROVIDER` | `qdrant` | Tells the app to connect to Qdrant Cloud instead of looking for local ChromaDB files |
| `HF_API_TOKEN` | `hf_your_token_here` | Authenticates with HuggingFace for embedding API calls |
| `QDRANT_URL` | `https://2522b98e-1be7-4ced-be02-853b0be095b4.sa-east-1-0.aws.cloud.qdrant.io:6333` | The address of your Qdrant Cloud cluster |
| `QDRANT_API_KEY` | `your_qdrant_api_key_here` | Authenticates with Qdrant Cloud |
| `XAI_API_KEY` | `your_groq_api_key_here` | Groq API key for LLM (llama-3.1-8b-instant) |
| `XAI_BASE_URL` | `https://api.groq.com/openai/v1` | Points the OpenAI SDK to Groq's endpoint |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Specifies which Groq model to use |
| `ENABLE_SCHEDULER` | `false` | Disables APScheduler — Railway does not allow background cron jobs |
| `CORS_ORIGINS` | `*` | Allows all browser origins to access the API (needed since Railway gives a random domain) |

> [!TIP]
> Use Railway's **"Add from .env"** button to paste multiple variables at once. Prepare a `.env.railway` file locally with just the production values listed above.

---

## Step 7 — Monitor the Build

After setting variables, Railway will automatically trigger a new build and deployment. Monitor it in the **"Deployments"** tab.

### What the Build Does (Automatically)

```
Stage 1 — Builder
  └─ pip install -r requirements.railway.txt (~200 MB)
     ├─ fastapi, uvicorn, gunicorn
     ├─ qdrant-client
     ├─ openai (for Groq)
     ├─ huggingface-hub
     └─ pydantic, python-dotenv, pytz

Stage 2 — Runtime Image (python:3.12-slim)
  ├─ Copies installed packages from Stage 1
  ├─ Copies backend/app/ code
  └─ Copies frontend/ static files

CMD: gunicorn app.main:app
     --worker-class uvicorn.workers.UvicornWorker
     --bind 0.0.0.0:${PORT}
     --workers 1
     --timeout 120
```

**Expected build time:** 2–4 minutes on first build (pip install caches on subsequent builds).

### What to Watch For

| Log Line | Meaning |
|---|---|
| `Successfully installed ...` | Dependencies installed OK |
| `Provider: api, VDB: qdrant, Scheduler: False` | App started in Railway mode |
| `Qdrant Cloud client connected to ...` | Database connection OK |
| `Application startup complete` | Ready to serve traffic |

---

## Step 8 — Verify the Deployment

Once the build succeeds, Railway will give you a public URL like `https://your-app-name.up.railway.app`.

### 8.1 — Health Check

Open in browser:
```
https://your-app-name.up.railway.app/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "Mutual Fund FAQ Assistant",
  "config": {
    "embedding_provider": "api",
    "vector_db_provider": "qdrant",
    "llm_model": "llama-3.1-8b-instant"
  }
}
```

If `embedding_provider` shows `"local"` or `vector_db_provider` shows `"chroma"`, the environment variables were not set correctly.

### 8.2 — Test a Chat Query

```powershell
curl -X POST https://your-app-name.up.railway.app/api/chat `
  -H "Content-Type: application/json" `
  -d '{"query": "What is the expense ratio of HDFC Mid Cap Fund?"}'
```

**Expected:** A factual answer mentioning 0.76% with a Groww citation.

### 8.3 — Open the UI

Visit `https://your-app-name.up.railway.app` in a browser. You should see the full chat interface.

---

## Step 9 — Set the Custom Domain (Optional)

If you want a cleaner URL (e.g., `hdfc-faq.yourdomain.com`) instead of the random Railway URL:

1. Go to Railway → Service → **"Settings"** → **"Custom Domain"**
2. Add your domain
3. Railway will give you a CNAME record to add at your DNS provider
4. Update `CORS_ORIGINS` to include your custom domain

---

## Ongoing Maintenance

### How to Update Fund Data (Re-ingestion)

When Groww updates the mutual fund data (expense ratios change, NAVs update, etc.):

1. Run ingestion locally in API mode — this re-scrapes Groww and re-uploads to Qdrant Cloud:

```powershell
cd "d:\RAG Chatbot\backend"
$env:EMBEDDING_PROVIDER="api"
$env:VECTOR_DB_PROVIDER="qdrant"
.\venv\Scripts\python.exe -m scripts.ingest
```

2. No Railway redeploy is needed — Railway's live app reads from Qdrant Cloud directly, so it will automatically serve the new data within seconds of the upload completing.

### How to Redeploy (Code Changes)

Any push to the `main` branch on GitHub will automatically trigger a Railway redeploy:

```powershell
git add .
git commit -m "fix: ..."
git push origin main
```

Railway will rebuild and redeploy with zero downtime using rolling deployments.

---

## Free Tier — Limits and Gotchas

> [!WARNING]
> Read these carefully to avoid unexpected issues.

| Limit | Impact | Mitigation |
|---|---|---|
| **Railway: 512 MB RAM** | App will crash if RAM exceeds this | Single Gunicorn worker keeps RAM at ~150 MB |
| **Railway: Sleeps after inactivity** | First request after idle period is slow (cold start ~5-10s) | Expected behavior; the HF API call adds ~1-2s on top |
| **Qdrant Cloud: Deletes free cluster after 4 weeks of zero traffic** | All vector data lost — chatbot stops answering | Visit the chatbot or ask it a question at least once a month |
| **HuggingFace API: Rate limited** | Embedding calls may be delayed or queued | The retry logic in `embedder.py` handles this automatically with exponential backoff |
| **Groq: 14,400 tokens/min free** | At ~1,000 tokens per query, that's ~14 queries/min | More than enough for a personal/demo project |
| **Railway: No persistent disk** | App cannot write files (log files, etc.) | All data is in Qdrant Cloud; no disk writes needed in production |

---

## Files Involved in Deployment

| File | Role |
|---|---|
| [railway.json](file:///d:/RAG%20Chatbot/railway.json) | Tells Railway which Dockerfile to use and sets the health check path |
| [backend/Dockerfile](file:///d:/RAG%20Chatbot/backend/Dockerfile) | Multi-stage build: installs slim deps, copies only app + frontend code |
| [backend/requirements.railway.txt](file:///d:/RAG%20Chatbot/backend/requirements.railway.txt) | Slim production dependencies (~200 MB, no torch, no playwright) |
| [.dockerignore](file:///d:/RAG%20Chatbot/.dockerignore) | Excludes chroma_data (543 MB), tests, docs, cache from Docker build context |
| [backend/app/config.py](file:///d:/RAG%20Chatbot/backend/app/config.py) | Reads all provider settings from environment variables |
| [backend/app/ingestion/embedder.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/embedder.py) | Dual-mode embedder: local or HuggingFace API |
| [backend/app/ingestion/vector_store.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/vector_store.py) | Dual-mode vector store: ChromaDB or Qdrant Cloud |
| [backend/app/ingestion/scheduler.py](file:///d:/RAG%20Chatbot/backend/app/ingestion/scheduler.py) | Conditional scheduler: disabled when `ENABLE_SCHEDULER=false` |

---

## References

| Document | Description |
|---|---|
| [architecture.md](file:///d:/RAG%20Chatbot/Docs/architecture.md) | Full system architecture including dual-mode diagram |
| [implementation-plan.md](file:///d:/RAG%20Chatbot/Docs/implementation-plan.md) | Phase 10 — Railway Migration implementation log |
| [Fix.txt](file:///d:/RAG%20Chatbot/Docs/Fix.txt) | Bug-fix log from 11-Jun-2026 testing |
