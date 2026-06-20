# ─────────────────────────────────────────────────────────────────
# Railway Deployment — Multi-stage Slim Build
# ─────────────────────────────────────────────────────────────────
# Build context must be the project root (RAG Chatbot/)
# Railway builds from: railway.json → dockerfilePath: "backend/Dockerfile"
# ─────────────────────────────────────────────────────────────────
# Final image: ~200 MB (vs ~3+ GB with local models)
# RAM usage:   ~100-150 MB (vs ~1.5+ GB with local models)
# ─────────────────────────────────────────────────────────────────

# Stage 1: Install dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only Railway-slim dependencies (no torch, no playwright, no chromadb)
COPY backend/requirements.railway.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy backend application code (only what's needed for serving)
COPY backend/app/ ./app/

# Copy frontend files for static serving
COPY frontend/ ./frontend/

# Railway injects PORT as an environment variable
ENV PORT=8000

# Use gunicorn with uvicorn workers for production
# --workers 1: Single worker to stay within 512 MB RAM
# --timeout 120: Allow time for first HF API call (cold start)
CMD gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --workers 1 \
    --timeout 120 \
    --graceful-timeout 30
