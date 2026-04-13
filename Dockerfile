# --- STAGE 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /build/rag-ui
COPY rag-ui/package*.json ./
RUN npm install
COPY rag-ui/ .
RUN npm run build

# --- STAGE 2: Python Backend & Final Image ---
FROM python:3.12-slim
WORKDIR /app

# System dependencies for ChromaDB/PDFs
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY config/ ./config/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /build/rag-ui/dist ./rag-ui/dist

# Ensure persistent directories exist
RUN mkdir -p chroma_db insights exports uploads

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
