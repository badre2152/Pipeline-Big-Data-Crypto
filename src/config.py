import os
from dotenv import load_dotenv

load_dotenv()


class MinioConfig:
    ENDPOINT   = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    SECURE     = os.getenv("MINIO_SECURE", "false").lower() == "true"

    BRONZE = "crypto-bronze"
    SILVER = "crypto-silver"
    GOLD   = "crypto-gold"


class SnowflakeConfig:
    ACCOUNT   = os.getenv("SNOWFLAKE_ACCOUNT")
    USER      = os.getenv("SNOWFLAKE_USER")
    PASSWORD  = os.getenv("SNOWFLAKE_PASSWORD")
    DATABASE  = os.getenv("SNOWFLAKE_DATABASE")
    SCHEMA    = os.getenv("SNOWFLAKE_SCHEMA", "public")
    WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")


class CoinGeckoConfig:
    BASE_URL    = "https://api.coingecko.com/api/v3"
    API_KEY     = os.getenv("COINGECKO_API_KEY")
    VS_CURRENCY = "usd"
    PER_PAGE    = 50        # top 50 cryptos
    PAGE        = 1
    TIMEOUT     = 30        # secondes
    MAX_RETRIES = 3
    RETRY_DELAY = 2         # secondes entre chaque retry