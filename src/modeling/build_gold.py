from __future__ import annotations

import io
from datetime import datetime, timezone
from src.utils.logger import get_logger

import pandas as pd

from src.config import MinioConfig
from src.clients.minio_client import get_minio_client, ensure_bucket_exists
from src.seeds.crypto_seeds import CATEGORIES, PLATFORMS, get_mapping

logger = get_logger(__name__)


# ─── LECTURE SILVER ──────────────────────────────────────────────────────────

def read_silver(client, date: datetime) -> pd.DataFrame:
    """
    Lit le fichier Parquet nettoyé depuis MinIO Silver pour la date donnée.
    """
    key = date.strftime("%Y/%m/%d/clean.parquet")

    try:
        response = client.get_object(Bucket=MinioConfig.SILVER, Key=key)
        buffer   = io.BytesIO(response["Body"].read())
        df       = pd.read_parquet(buffer, engine="pyarrow")
        logger.info(f"Read Silver: s3://{MinioConfig.SILVER}/{key} — {len(df)} rows")
        return df

    except client.exceptions.NoSuchKey:
        raise FileNotFoundError(f"Silver file not found: s3://{MinioConfig.SILVER}/{key}")


# ─── DIMENSIONS ──────────────────────────────────────────────────────────────

def build_dim_category() -> pd.DataFrame:
    """
    Construit dim_category depuis les seeds hardcodées.
    Aucun appel API — données de référence statiques.
    """
    df = pd.DataFrame(CATEGORIES)
    logger.info(f"dim_category: {len(df)} rows")
    return df


def build_dim_platform() -> pd.DataFrame:
    """
    Construit dim_platform depuis les seeds hardcodées.
    Aucun appel API — données de référence statiques.
    """
    df = pd.DataFrame(PLATFORMS)
    logger.info(f"dim_platform: {len(df)} rows")
    return df


def build_dim_crypto(df_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Construit dim_crypto depuis Silver + seeds.
    Colonnes : crypto_key, coin_id, name, symbol, category_key, platform_key
    """
    dim = df_silver[["coin_id", "name", "symbol"]].drop_duplicates("coin_id").copy()

    # Appliquer le mapping seeds → category_key + platform_key
    dim["category_key"] = dim["coin_id"].apply(lambda x: get_mapping(x)["category_key"])
    dim["platform_key"] = dim["coin_id"].apply(lambda x: get_mapping(x)["platform_key"])

    # Surrogate key
    dim.insert(0, "crypto_key", range(1, len(dim) + 1))
    dim.reset_index(drop=True, inplace=True)

    logger.info(f"dim_crypto: {len(dim)} rows")
    return dim


def build_dim_date(dates: pd.Series) -> pd.DataFrame:
    """
    Construit dim_date depuis les dates présentes dans Silver.
    date_key au format YYYYMMDD (ex: 20250115).
    """
    unique_dates = pd.to_datetime(dates.dt.date.unique())
    rows = []

    for d in unique_dates:
        rows.append({
            "date_key":   int(d.strftime("%Y%m%d")),
            "full_date":  d.date(),
            "year":       d.year,
            "quarter":    d.quarter,
            "month":      d.month,
            "month_name": d.strftime("%B"),
            "week":       int(d.strftime("%V")),  # ISO week
            "day":        d.day,
            "day_name":   d.strftime("%A"),
            "is_weekend": d.weekday() >= 5,
        })

    df = pd.DataFrame(rows).sort_values("date_key").reset_index(drop=True)
    df["date_key"] = df["date_key"].astype("int64")
    logger.info(f"dim_date: {len(df)} rows")
    return df


# ─── TABLE DE FAITS ──────────────────────────────────────────────────────────

def build_fact_crypto_prices(
    df_silver: pd.DataFrame,
    dim_crypto: pd.DataFrame,
    dim_date: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construit fact_crypto_prices en résolvant toutes les clés étrangères.
    Grain : une ligne par crypto par jour.
    Vérifie l'intégrité référentielle avant de retourner.
    """
    fact = df_silver.copy()

    # ── Résolution crypto_key ─────────────────────────────────────────────
    crypto_lookup = dim_crypto[["coin_id", "crypto_key", "category_key", "platform_key"]]
    fact = fact.merge(crypto_lookup, on="coin_id", how="left")

    unresolved_crypto = fact["crypto_key"].isna().sum()
    if unresolved_crypto > 0:
        logger.warning(f"{unresolved_crypto} rows with unresolved crypto_key — dropping.")
        fact.dropna(subset=["crypto_key"], inplace=True)

    # ── Résolution date_key ───────────────────────────────────────────────
    fact["date_key"] = fact["collected_at"].dt.strftime("%Y%m%d").astype(int)

    valid_date_keys = set(dim_date["date_key"].tolist())
    unresolved_date = (~fact["date_key"].isin(valid_date_keys)).sum()
    if unresolved_date > 0:
        raise ValueError(f"{unresolved_date} rows with date_key not in dim_date.")

    # ── Sélection et ordre final ──────────────────────────────────────────
    fact = fact[[
        "crypto_key",
        "date_key",
        "category_key",
        "platform_key",
        "current_price",
        "high_24h",
        "low_24h",
        "price_change_24h",
        "price_change_pct_24h",
        "total_volume",
        "market_cap",
        "market_cap_rank",
    ]].copy()

    # Surrogate key — crypto_key + date_key = unique sur toute la durée du pipeline
    # int64 explicite — sur Windows, pandas peut utiliser int32 par défaut,
    # ce qui cause un overflow car crypto_key+date_key dépasse 2^31.
    fact.insert(0, "fact_id", (fact["crypto_key"].astype(str) + fact["date_key"].astype(str)).astype("int64"))

    # Cast types — int64 explicite pour compatibilité cross-platform (Windows/Mac/Linux)
    for col in ["crypto_key", "date_key", "category_key", "platform_key", "market_cap_rank", "fact_id"]:
        fact[col] = fact[col].astype("int64")

    logger.info(f"fact_crypto_prices: {len(fact)} rows")
    return fact


# ─── VALIDATION INTÉGRITÉ RÉFÉRENTIELLE ─────────────────────────────────────

def validate_referential_integrity(
    fact: pd.DataFrame,
    dim_crypto: pd.DataFrame,
    dim_date: pd.DataFrame,
    dim_category: pd.DataFrame,
    dim_platform: pd.DataFrame,
) -> None:
    """
    Vérifie que toutes les FK dans fact_crypto_prices pointent
    vers des PK valides dans les dimensions.
    """
    checks = [
        (fact["crypto_key"],   dim_crypto["crypto_key"],   "crypto_key"),
        (fact["date_key"],     dim_date["date_key"],       "date_key"),
        (fact["category_key"], dim_category["category_key"], "category_key"),
        (fact["platform_key"], dim_platform["platform_key"], "platform_key"),
    ]

    for fk_series, pk_series, name in checks:
        orphans = ~fk_series.isin(pk_series)
        if orphans.any():
            raise ValueError(f"Referential integrity violation: {orphans.sum()} orphan rows on {name}.")

    logger.info("Referential integrity validation passed.")


# ─── SAUVEGARDE GOLD ─────────────────────────────────────────────────────────

def save_to_gold(client, df: pd.DataFrame, table_name: str, date: datetime) -> str:
    """
    Sauvegarde une table Gold en Parquet dans MinIO.
    Format du chemin : crypto-gold/YYYY/MM/DD/{table_name}.parquet
    """
    ensure_bucket_exists(client, MinioConfig.GOLD)

    key    = date.strftime(f"%Y/%m/%d/{table_name}.parquet")
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)

    client.put_object(
        Bucket=MinioConfig.GOLD,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )

    logger.info(f"Saved to Gold: s3://{MinioConfig.GOLD}/{key}")
    return key


# ─── ENTRYPOINT ──────────────────────────────────────────────────────────────

def build_gold(date: datetime = None) -> dict[str, str]:
    """
    Point d'entrée principal — appelé par pipeline.py et le DAG Airflow.
    Construit toutes les tables Gold et les sauvegarde dans MinIO.
    Retourne un dict {table_name: s3_key}.
    """
    if date is None:
        date = datetime.now(timezone.utc)

    logger.info(f"Starting Gold modeling for {date.strftime('%Y-%m-%d')}")

    client = get_minio_client()

    # 1. Lire Silver
    df_silver = read_silver(client, date)

    # 2. Construire les dimensions
    dim_category = build_dim_category()
    dim_platform = build_dim_platform()
    dim_crypto   = build_dim_crypto(df_silver)
    dim_date     = build_dim_date(df_silver["collected_at"])

    # 3. Construire la table de faits
    fact = build_fact_crypto_prices(df_silver, dim_crypto, dim_date)

    # 4. Valider l'intégrité référentielle
    validate_referential_integrity(fact, dim_crypto, dim_date, dim_category, dim_platform)

    # 5. Sauvegarder toutes les tables
    saved = {}
    tables = {
        "fact_crypto_prices": fact,
        "dim_crypto":         dim_crypto,
        "dim_date":           dim_date,
        "dim_category":       dim_category,
        "dim_platform":       dim_platform,
    }

    for table_name, df in tables.items():
        key = save_to_gold(client, df, table_name, date)
        saved[table_name] = key

    logger.info(f"Gold modeling complete — {len(saved)} tables saved.")
    return saved


if __name__ == "__main__":
    build_gold()