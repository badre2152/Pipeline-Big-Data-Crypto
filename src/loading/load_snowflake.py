import io
import logging
from datetime import datetime, timezone
from src.utils.logger import get_logger
import pandas as pd

from src.config import MinioConfig
from src.clients.minio_client import get_minio_client
from src.clients.snowflake_client import get_snowflake_connection, execute, executemany, fetchall

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─── DDL — CRÉATION DU SCHÉMA ────────────────────────────────────────────────

DDL_STATEMENTS = [

    """
    CREATE TABLE IF NOT EXISTS dim_category (
        category_key    INT           PRIMARY KEY,
        category_name   VARCHAR(100)  NOT NULL UNIQUE,
        category_desc   VARCHAR(255)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS dim_platform (
        platform_key    INT           PRIMARY KEY,
        platform_name   VARCHAR(100)  NOT NULL UNIQUE,
        blockchain      VARCHAR(100)  NOT NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS dim_crypto (
        crypto_key      INT           PRIMARY KEY,
        coin_id         VARCHAR(100)  NOT NULL UNIQUE,
        name            VARCHAR(100)  NOT NULL,
        symbol          VARCHAR(20)   NOT NULL,
        category_key    INT           NOT NULL REFERENCES dim_category(category_key),
        platform_key    INT           NOT NULL REFERENCES dim_platform(platform_key)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS dim_date (
        date_key        INT           PRIMARY KEY,
        full_date       DATE          NOT NULL UNIQUE,
        year            INT           NOT NULL,
        quarter         INT           NOT NULL,
        month           INT           NOT NULL,
        month_name      VARCHAR(20)   NOT NULL,
        week            INT           NOT NULL,
        day             INT           NOT NULL,
        day_name        VARCHAR(20)   NOT NULL,
        is_weekend      BOOLEAN       NOT NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS fact_crypto_prices (
        fact_id               INT     PRIMARY KEY,
        crypto_key            INT     NOT NULL REFERENCES dim_crypto(crypto_key),
        date_key              INT     NOT NULL REFERENCES dim_date(date_key),
        category_key          INT     NOT NULL REFERENCES dim_category(category_key),
        platform_key          INT     NOT NULL REFERENCES dim_platform(platform_key),
        current_price         FLOAT   NOT NULL,
        high_24h              FLOAT   NOT NULL,
        low_24h               FLOAT   NOT NULL,
        price_change_24h      FLOAT   NOT NULL,
        price_change_pct_24h  FLOAT   NOT NULL,
        total_volume          FLOAT   NOT NULL,
        market_cap            FLOAT   NOT NULL,
        market_cap_rank       INT     NOT NULL
    )
    """,
]


# ─── LECTURE GOLD ────────────────────────────────────────────────────────────

def read_gold_table(client, table_name: str, date: datetime) -> pd.DataFrame:
    """
    Lit une table Gold depuis MinIO en Parquet.
    Format du chemin : crypto-gold/YYYY/MM/DD/{table_name}.parquet
    """
    key = date.strftime(f"%Y/%m/%d/{table_name}.parquet")

    try:
        response = client.get_object(Bucket=MinioConfig.GOLD, Key=key)
        buffer   = io.BytesIO(response["Body"].read())
        df       = pd.read_parquet(buffer, engine="pyarrow")
        logger.info(f"Read Gold: {table_name} — {len(df)} rows")
        return df

    except client.exceptions.NoSuchKey:
        raise FileNotFoundError(f"Gold file not found: s3://{MinioConfig.GOLD}/{key}")


# ─── CRÉATION DU SCHÉMA ──────────────────────────────────────────────────────

def create_schema(conn) -> None:
    """
    Crée toutes les tables du schéma dimensionnel dans Snowflake.
    IF NOT EXISTS — idempotent, safe à relancer.
    L'ordre respecte les dépendances FK :
    dim_category → dim_platform → dim_crypto → dim_date → fact
    """
    logger.info("Creating Snowflake schema...")
    for ddl in DDL_STATEMENTS:
        execute(conn, ddl)
    logger.info("Schema created successfully.")


# ─── CHARGEMENT DES TABLES ───────────────────────────────────────────────────

def upsert_dim_category(conn, df: pd.DataFrame) -> None:
    """
    Charge dim_category — MERGE pour éviter les doublons sur relance.
    Seeds stables — rarement modifiées.
    """
    sql = """
        MERGE INTO dim_category AS target
        USING (SELECT %s AS category_key, %s AS category_name, %s AS category_desc) AS source
        ON target.category_key = source.category_key
        WHEN NOT MATCHED THEN
            INSERT (category_key, category_name, category_desc)
            VALUES (source.category_key, source.category_name, source.category_desc)
    """
    data = [
        (row["category_key"], row["category_name"], row.get("category_desc"))
        for _, row in df.iterrows()
    ]
    executemany(conn, sql, data)
    logger.info(f"dim_category: {len(data)} rows upserted.")


def upsert_dim_platform(conn, df: pd.DataFrame) -> None:
    """Charge dim_platform — MERGE pour idempotence."""
    sql = """
        MERGE INTO dim_platform AS target
        USING (SELECT %s AS platform_key, %s AS platform_name, %s AS blockchain) AS source
        ON target.platform_key = source.platform_key
        WHEN NOT MATCHED THEN
            INSERT (platform_key, platform_name, blockchain)
            VALUES (source.platform_key, source.platform_name, source.blockchain)
    """
    data = [
        (row["platform_key"], row["platform_name"], row["blockchain"])
        for _, row in df.iterrows()
    ]
    executemany(conn, sql, data)
    logger.info(f"dim_platform: {len(data)} rows upserted.")


def upsert_dim_crypto(conn, df: pd.DataFrame) -> None:
    """Charge dim_crypto — MERGE sur coin_id (stable dans le temps)."""
    sql = """
        MERGE INTO dim_crypto AS target
        USING (SELECT %s AS crypto_key, %s AS coin_id, %s AS name,
                      %s AS symbol, %s AS category_key, %s AS platform_key) AS source
        ON target.coin_id = source.coin_id
        WHEN NOT MATCHED THEN
            INSERT (crypto_key, coin_id, name, symbol, category_key, platform_key)
            VALUES (source.crypto_key, source.coin_id, source.name,
                    source.symbol, source.category_key, source.platform_key)
    """
    data = [
        (row["crypto_key"], row["coin_id"], row["name"],
         row["symbol"], row["category_key"], row["platform_key"])
        for _, row in df.iterrows()
    ]
    executemany(conn, sql, data)
    logger.info(f"dim_crypto: {len(data)} rows upserted.")


def upsert_dim_date(conn, df: pd.DataFrame) -> None:
    """Charge dim_date — MERGE sur date_key (YYYYMMDD)."""
    sql = """
        MERGE INTO dim_date AS target
        USING (SELECT %s AS date_key, %s AS full_date, %s AS year, %s AS quarter,
                      %s AS month, %s AS month_name, %s AS week,
                      %s AS day, %s AS day_name, %s AS is_weekend) AS source
        ON target.date_key = source.date_key
        WHEN NOT MATCHED THEN
            INSERT (date_key, full_date, year, quarter, month, month_name,
                    week, day, day_name, is_weekend)
            VALUES (source.date_key, source.full_date, source.year, source.quarter,
                    source.month, source.month_name, source.week,
                    source.day, source.day_name, source.is_weekend)
    """
    data = [
        (row["date_key"], str(row["full_date"]), row["year"], row["quarter"],
         row["month"], row["month_name"], row["week"],
         row["day"], row["day_name"], bool(row["is_weekend"]))
        for _, row in df.iterrows()
    ]
    executemany(conn, sql, data)
    logger.info(f"dim_date: {len(data)} rows upserted.")


def insert_fact(conn, df: pd.DataFrame) -> None:
    """
    Insère les lignes de fact_crypto_prices.
    INSERT simple — chaque jour génère de nouvelles lignes.
    On vérifie d'abord qu'il n'y a pas de doublons sur (crypto_key, date_key).
    """
    # Vérification anti-doublon
    date_keys = df["date_key"].unique().tolist()
    # Snowflake ne supporte pas %s dans IN(...) via fetchall — on inline les valeurs directement
    if date_keys:
        keys_str = ", ".join(str(k) for k in date_keys)
        existing = fetchall(
            conn,
            f"SELECT DISTINCT date_key FROM fact_crypto_prices WHERE date_key IN ({keys_str})"
        )
    else:
        existing = []
    existing_keys = {row["DATE_KEY"] for row in existing}

    already_loaded = df["date_key"].isin(existing_keys)
    if already_loaded.any():
        logger.warning(f"Skipping {already_loaded.sum()} rows already loaded for date_key(s): {existing_keys}")
        df = df[~already_loaded].copy()

    if df.empty:
        logger.info("fact_crypto_prices: nothing new to insert.")
        return

    sql = """
        INSERT INTO fact_crypto_prices (
            fact_id, crypto_key, date_key, category_key, platform_key,
            current_price, high_24h, low_24h,
            price_change_24h, price_change_pct_24h,
            total_volume, market_cap, market_cap_rank
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    import math

    def _val(v, fallback=None):
        """Convertit NaN/Inf en fallback pour Snowflake."""
        if v is None:
            return fallback
        try:
            if math.isnan(v) or math.isinf(v):
                return fallback
        except (TypeError, ValueError):
            pass
        return v

    data = [
        (
            _val(row["fact_id"]),
            _val(row["crypto_key"]),
            _val(row["date_key"]),
            _val(row["category_key"]),
            _val(row["platform_key"]),
            _val(row["current_price"],        fallback=0.0),
            _val(row["high_24h"],             fallback=_val(row["current_price"], 0.0)),
            _val(row["low_24h"],              fallback=_val(row["current_price"], 0.0)),
            _val(row["price_change_24h"],     fallback=0.0),
            _val(row["price_change_pct_24h"], fallback=0.0),
            _val(row["total_volume"],         fallback=0.0),
            _val(row["market_cap"],           fallback=0.0),
            _val(row["market_cap_rank"],      fallback=0),
        )
        for _, row in df.iterrows()
    ]
    executemany(conn, sql, data)
    logger.info(f"fact_crypto_prices: {len(data)} rows inserted.")


# ─── VALIDATION POST-LOAD ────────────────────────────────────────────────────

def validate_load(conn, date: datetime) -> None:
    """
    Vérifie que les données ont bien été chargées dans Snowflake
    pour la date du run.
    """
    date_key = int(date.strftime("%Y%m%d"))
    result   = fetchall(
        conn,
        f"SELECT COUNT(*) AS cnt FROM fact_crypto_prices WHERE date_key = {date_key}"
    )
    count = result[0]["CNT"]

    if count == 0:
        raise ValueError(f"Validation failed: 0 rows in fact_crypto_prices for date_key={date_key}")

    logger.info(f"Validation passed: {count} rows in fact_crypto_prices for date_key={date_key}.")


# ─── ENTRYPOINT ──────────────────────────────────────────────────────────────

def load_snowflake(date: datetime = None) -> None:
    """
    Point d'entrée principal — appelé par pipeline.py et le DAG Airflow.
    Ordre de chargement respecte les dépendances FK :
    dim_category → dim_platform → dim_crypto → dim_date → fact
    """
    if date is None:
        date = datetime.now(timezone.utc)

    logger.info(f"Starting Snowflake load for {date.strftime('%Y-%m-%d')}")

    minio_client = get_minio_client()
    conn         = get_snowflake_connection()

    try:
        # 1. Créer le schéma si nécessaire
        create_schema(conn)

        # 2. Lire les tables Gold depuis MinIO
        dim_category = read_gold_table(minio_client, "dim_category", date)
        dim_platform = read_gold_table(minio_client, "dim_platform", date)
        dim_crypto   = read_gold_table(minio_client, "dim_crypto",   date)
        dim_date     = read_gold_table(minio_client, "dim_date",     date)
        fact         = read_gold_table(minio_client, "fact_crypto_prices", date)

        # 3. Charger dans l'ordre des dépendances FK
        upsert_dim_category(conn, dim_category)
        upsert_dim_platform(conn, dim_platform)
        upsert_dim_crypto(conn, dim_crypto)
        upsert_dim_date(conn, dim_date)
        insert_fact(conn, fact)

        # 4. Valider
        validate_load(conn, date)

        logger.info("Snowflake load complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    load_snowflake()