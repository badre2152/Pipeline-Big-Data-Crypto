from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import requests

from src.config import CoinGeckoConfig, MinioConfig
from src.clients.minio_client import get_minio_client, ensure_bucket_exists
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ─── API ────────────────────────────────────────────────────────────────────

def fetch_top_cryptos() -> list[dict]:
    url = f"{CoinGeckoConfig.BASE_URL}/coins/markets"
    params = {
        "vs_currency": CoinGeckoConfig.VS_CURRENCY,
        "order":       "market_cap_desc",
        "per_page":    CoinGeckoConfig.PER_PAGE,
        "page":        CoinGeckoConfig.PAGE,
        "sparkline":   False,
    }

    for attempt in range(1, CoinGeckoConfig.MAX_RETRIES + 1):
        try:
            logger.info(f"Fetching CoinGecko — attempt {attempt}/{CoinGeckoConfig.MAX_RETRIES}")

            headers = {}
            if CoinGeckoConfig.API_KEY:
                headers["x-cg-demo-api-key"] = CoinGeckoConfig.API_KEY

            response = requests.get(
                url, params=params, headers=headers,
                timeout=CoinGeckoConfig.TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data)} cryptos successfully.")
            return data

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt}.")

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait = CoinGeckoConfig.RETRY_DELAY * attempt * 3
                logger.warning(f"Rate limited (429). Waiting {wait}s before retry.")
                time.sleep(wait)
            else:
                logger.error(f"HTTP error: {e}")
                raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

        if attempt < CoinGeckoConfig.MAX_RETRIES:
            time.sleep(CoinGeckoConfig.RETRY_DELAY)

    raise RuntimeError(f"Failed to fetch CoinGecko data after {CoinGeckoConfig.MAX_RETRIES} attempts.")


# ─── MINIO ──────────────────────────────────────────────────────────────────

def build_bronze_key(collected_at: datetime) -> str:
    return collected_at.strftime("%Y/%m/%d/raw.json")


def save_to_bronze(data: list[dict], collected_at: datetime) -> str:
    client = get_minio_client()
    ensure_bucket_exists(client, MinioConfig.BRONZE)

    payload = {
        "collected_at": collected_at.isoformat(),
        "source":       "coingecko/coins/markets",
        "vs_currency":  CoinGeckoConfig.VS_CURRENCY,
        "count":        len(data),
        "data":         data,
    }

    key  = build_bronze_key(collected_at)
    body = json.dumps(payload, ensure_ascii=False, indent=2)

    client.put_object(
        Bucket=MinioConfig.BRONZE,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )

    logger.info(f"Saved to Bronze: s3://{MinioConfig.BRONZE}/{key}")
    return key


# ─── ENTRYPOINT ─────────────────────────────────────────────────────────────

def ingest_bronze() -> str:
    collected_at = datetime.now(timezone.utc)
    logger.info(f"Starting Bronze ingestion at {collected_at.isoformat()}")
    data = fetch_top_cryptos()
    key  = save_to_bronze(data, collected_at)
    logger.info("Bronze ingestion complete.")
    return key


if __name__ == "__main__":
    ingest_bronze()