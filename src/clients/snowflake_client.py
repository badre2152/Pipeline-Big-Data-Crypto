from __future__ import annotations

import snowflake.connector
from snowflake.connector import DictCursor
from src.config import SnowflakeConfig


def get_snowflake_connection():
    """
    Retourne une connexion Snowflake active.
    Crée la DATABASE et le SCHEMA automatiquement s'ils n'existent pas.
    À fermer explicitement après usage : conn.close()
    """
    # 1. Connexion sans database/schema — pour pouvoir créer s'ils n'existent pas
    conn = snowflake.connector.connect(
        account=SnowflakeConfig.ACCOUNT,
        user=SnowflakeConfig.USER,
        password=SnowflakeConfig.PASSWORD,
        warehouse=SnowflakeConfig.WAREHOUSE,
    )

    with conn.cursor() as cur:
        # 2. Activer le warehouse
        if SnowflakeConfig.WAREHOUSE:
            cur.execute(f"USE WAREHOUSE {SnowflakeConfig.WAREHOUSE}")

        # 3. Créer la database si elle n'existe pas
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {SnowflakeConfig.DATABASE}")
        cur.execute(f"USE DATABASE {SnowflakeConfig.DATABASE}")

        # 4. Créer le schema s'il n'existe pas
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SnowflakeConfig.SCHEMA}")
        cur.execute(f"USE SCHEMA {SnowflakeConfig.SCHEMA}")

    return conn


def execute(conn, sql: str, params: tuple = None) -> None:
    """Exécute une requête SQL sans retour de résultat."""
    with conn.cursor() as cur:
        cur.execute(sql, params)


def executemany(conn, sql: str, data: list[tuple]) -> None:
    """Exécute une requête SQL en batch (INSERT multiple)."""
    with conn.cursor() as cur:
        cur.executemany(sql, data)


def fetchall(conn, sql: str) -> list[dict]:
    """Exécute une requête SELECT et retourne les résultats en liste de dicts."""
    with conn.cursor(DictCursor) as cur:
        cur.execute(sql)
        return cur.fetchall()