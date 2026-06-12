from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pandas as pd

from src.config import MinioConfig
from src.clients.minio_client import get_minio_client, ensure_bucket_exists
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── COLONNES ATTENDUES ──────────────────────────────────────────────────────

EXPECTED_COLUMNS = [
    "id", "symbol", "name",
    "current_price", "market_cap", "market_cap_rank",
    "total_volume", "high_24h", "low_24h",
    "price_change_24h", "price_change_percentage_24h",
    "last_updated",
]

COLUMN_RENAME_MAP = {
    "id":                          "coin_id",
    "price_change_percentage_24h": "price_change_pct_24h",
    "last_updated":                "collected_at",
}

NUMERIC_COLUMNS = [
    "current_price", "market_cap", "market_cap_rank",
    "total_volume", "high_24h", "low_24h",
    "price_change_24h", "price_change_pct_24h",
]


# ─── LECTURE BRONZE ──────────────────────────────────────────────────────────

def read_bronze(client, date: datetime) -> list[dict]:
    key = date.strftime("%Y/%m/%d/raw.json")
    try:
        response = client.get_object(Bucket=MinioConfig.BRONZE, Key=key)
        raw      = response["Body"].read().decode("utf-8")
        payload  = json.loads(raw)
        logger.info(f"Read Bronze: s3://{MinioConfig.BRONZE}/{key} — {payload['count']} records")
        return payload["data"]
    except client.exceptions.NoSuchKey:
        raise FileNotFoundError(f"Bronze file not found: s3://{MinioConfig.BRONZE}/{key}")


# ─── NETTOYAGE ───────────────────────────────────────────────────────────────

def clean(data: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(data)

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns from CoinGecko response: {missing}")
    df = df[EXPECTED_COLUMNS].copy()

    df.rename(columns=COLUMN_RENAME_MAP, inplace=True)

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df.dropna(subset=["coin_id", "current_price", "market_cap"], inplace=True)
    after = len(df)
    if before != after:
        logger.warning(f"Dropped {before - after} rows with null critical values.")

    df["symbol"]       = df["symbol"].str.upper().str.strip()
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True)
    df.reset_index(drop=True, inplace=True)

    logger.info(f"Cleaned DataFrame: {len(df)} rows, {len(df.columns)} columns.")
    return df


# ─── VALIDATION ──────────────────────────────────────────────────────────────

def validate_silver(df: pd.DataFrame) -> None:
    if len(df) == 0:
        raise ValueError("Silver DataFrame is empty.")
    if not df["coin_id"].is_unique:
        raise ValueError("coin_id must be unique per batch.")
    if not df["current_price"].gt(0).all():
        raise ValueError("current_price must be > 0.")
    if not df["market_cap"].ge(0).all():
        raise ValueError("market_cap must be >= 0.")
    if df["market_cap_rank"].isna().any():
        raise ValueError("market_cap_rank must not be null.")
    logger.info("Silver validation passed.")


# ─── SAUVEGARDE SILVER ───────────────────────────────────────────────────────

def save_to_silver(client, df: pd.DataFrame, date: datetime) -> str:
    ensure_bucket_exists(client, MinioConfig.SILVER)

    key    = date.strftime("%Y/%m/%d/clean.parquet")
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)

    client.put_object(
        Bucket=MinioConfig.SILVER,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )

    logger.info(f"Saved to Silver: s3://{MinioConfig.SILVER}/{key}")
    return key


# ─── ENTRYPOINT ──────────────────────────────────────────────────────────────

def transform_silver(date: datetime = None) -> str:
    if date is None:
        date = datetime.now(timezone.utc)

    logger.info(f"Starting Silver transformation for {date.strftime('%Y-%m-%d')}")

    client = get_minio_client()
    data   = read_bronze(client, date)
    df     = clean(data)
    validate_silver(df)
    key    = save_to_silver(client, df, date)

    logger.info("Silver transformation complete.")
    return key


if __name__ == "__main__":
    transform_silver()