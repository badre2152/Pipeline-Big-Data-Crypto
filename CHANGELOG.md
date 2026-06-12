# Changelog

All notable changes to this project are documented here.

---

## [1.0.0] — 2025-06-09

### Added
- **Étape 5** — Airflow DAG `crypto_pipeline_dag` with daily scheduling at 06:00 UTC
- **Étape 5** — Manual orchestrator `pipeline.py` with `--date` and `--steps` CLI args
- `pipeline.py` supports partial runs (e.g. `--steps bronze silver`) for debugging

## [0.4.0] — 2025-06-09

### Added
- **Étape 4** — `load_snowflake.py`: DDL creation, MERGE upsert for dimensions, INSERT with anti-duplicate check for fact table
- **Étape 4** — `snowflake_client.py`: reusable Snowflake connection wrapper

## [0.3.0] — 2025-06-09

### Added
- **Étape 3** — `build_gold.py`: constructs all 5 dimensional tables from Silver
- **Étape 3** — `crypto_seeds.py`: hardcoded reference data for `dim_category` and `dim_platform` (intentional — avoids CoinGecko free tier rate limits)
- Referential integrity validation before Gold save

## [0.2.0] — 2025-06-09

### Added
- **Étape 2** — `transform_silver.py`: cleaning, snake_case normalization, Parquet output
- Silver validation: unique `coin_id`, positive prices, non-null ranks

## [0.1.0] — 2025-06-09

### Added
- **Étape 0** — Snowflake Schema design and ERD (dbdiagram.io)
- **Étape 0** — End-to-end architecture diagram
- **Étape 1** — `ingest_bronze.py`: CoinGecko API → MinIO Bronze with retry logic
- `minio_client.py`: reusable MinIO connection wrapper
- `config.py`: centralized environment configuration
- `.env.example`: environment variable template
- Project structure: `src/{ingestion,transformation,modeling,loading,clients,seeds,utils,dags}`