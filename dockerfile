FROM python:3.10-slim

# ── Metadata ────────────────────────────────────────────────
LABEL maintainer="brahim badre"
LABEL description="Crypto Data Pipeline — CoinGecko → MinIO → Snowflake"

# ── Working directory ────────────────────────────────────────
WORKDIR /app

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Project source ───────────────────────────────────────────
COPY src/ ./src/
COPY .env.example .env

# ── Entrypoint ───────────────────────────────────────────────
CMD ["python", "-m", "src.pipeline"]