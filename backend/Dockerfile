# Multi-stage Dockerfile for LexOrch-KG Backend

# ── Build Stage ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime Stage ───────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p /app/data /app/logs /app/outputs

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
