# Crypto Data Pipeline

End-to-end data pipeline for cryptocurrency market data — from CoinGecko API ingestion to Tableau dashboards, built on a Medallion architecture with a Snowflake Schema dimensional model.

---

## Architecture

```
CoinGecko API
      │ JSON
      ▼
┌─────────────────────────────────────┐
│           MinIO  (Data Lake)        │
│  Bronze        Silver        Gold   │
│  raw JSON  →  Parquet   →  Parquet  │
│              (cleaned)  (dim model) │
└─────────────────────────────────────┘
      │ Parquet
      ▼
  Snowflake  (Data Warehouse)
      │ ODBC
      ▼
   Tableau  (Dashboards)

Orchestration : Apache Airflow (daily at 06:00 UTC)
```

## Data Model — Snowflake Schema

```
dim_category ◄─── dim_crypto ───► dim_platform
                      │
              fact_crypto_prices
                      │
                  dim_date
```

**fact_crypto_prices** — grain: one row per crypto per day
`current_price`, `high_24h`, `low_24h`, `price_change_24h`, `price_change_pct_24h`, `total_volume`, `market_cap`, `market_cap_rank`

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-username/crypto-pipeline.git
cd crypto-pipeline

# 2. Environment
cp .env.example .env
# Fill in MinIO and Snowflake credentials

# 3. Install dependencies
pip install -r requirements-dev.txt

# 4. Start MinIO + Airflow
docker-compose up -d

# 5. Run pipeline manually
python -m src.pipeline

# Run for a specific date
python -m src.pipeline --date 2025-01-15

# Run specific steps only
python -m src.pipeline --steps bronze silver
```

---

## Project Structure

```
crypto-pipeline/
├── src/
│   ├── ingestion/          # Étape 1 — CoinGecko → MinIO Bronze
│   ├── transformation/     # Étape 2 — Bronze → Silver (Parquet)
│   ├── modeling/           # Étape 3 — Silver → Gold (dimensional model)
│   ├── loading/            # Étape 4 — Gold → Snowflake
│   ├── clients/            # MinIO + Snowflake connection wrappers
│   ├── seeds/              # Reference data (dim_category, dim_platform)
│   ├── dags/               # Airflow DAG
│   ├── utils/              # Shared utilities
│   └── config.py           # Centralized environment config
├── tests/                  # Mirrors src/ structure
├── docs/
│   └── decisions/          # Architecture Decision Records (ADRs)
├── notebook/               # Exploration and validation
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── setup.cfg
└── CHANGELOG.md
```

---

## Stack

| Layer | Tool |
|-------|------|
| Source | CoinGecko API (free tier) |
| Data Lake | MinIO (S3-compatible) |
| Transformation | Python, Pandas, PyArrow |
| Orchestration | Apache Airflow |
| Data Warehouse | Snowflake |
| BI | Tableau |

---

## Key Design Decisions

- **Snowflake Schema** over Star Schema — `dim_category` and `dim_platform` normalized to avoid redundancy. See [ADR 001](docs/decisions/001-snowflake-schema.md).
- **Hardcoded seed data** for `dim_category` and `dim_platform` — avoids CoinGecko free tier rate limits. Pattern known as "reference data" in production. See [ADR 002](docs/decisions/002-hardcoded-seeds.md).
- **Idempotent loads** — MERGE for dimensions, anti-duplicate check for fact table. Safe to re-run.
- **Envelope pattern** in Bronze — raw JSON wrapped with `collected_at`, `source`, `count` metadata.

---

## Running Tests

```bash
pytest
pytest --cov=src tests/
```

---

## Environment Variables

See `.env.example` for the full list. Required variables:

```
MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA, SNOWFLAKE_WAREHOUSE
```