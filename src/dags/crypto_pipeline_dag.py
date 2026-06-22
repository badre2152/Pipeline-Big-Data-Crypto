"""
crypto_pipeline_dag.py
======================
DAG principal du pipeline crypto — scheduling quotidien.

Ordre des tâches :
    ingest_bronze >> transform_silver >> build_gold_model >> load_snowflake

Chaque tâche est indépendante et appelle directement
les fonctions des modules src/.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.ingestion.ingest_bronze import ingest_bronze
from src.transformation.transform_silver import transform_silver
from src.modeling.build_gold import build_gold
from src.loading.load_snowflake import load_snowflake


# ─── ARGUMENTS PAR DÉFAUT ────────────────────────────────────────────────────

DEFAULT_ARGS = {
    "owner":            "crypto-pipeline",
    "depends_on_past":  False,
    "email_on_failure": False,       # passer à True en production avec email SMTP
    "email_on_retry":   False,
    "retries":          3,
    "retry_delay":      timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}


# ─── DAG ─────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="crypto_pipeline_dag",
    description="Pipeline quotidien : CoinGecko → Bronze → Silver → Gold → Snowflake",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 6, 15),
    schedule_interval="0 11 * * *",  # tous les jours à 11h00
    catchup=False,                   # pas de backfill automatique
    max_active_runs=1,               # une seule exécution à la fois
    tags=["crypto", "pipeline", "daily"],
) as dag:


    # ── TASK 1 — Bronze ───────────────────────────────────────────────────────
    task_ingest_bronze = PythonOperator(
        task_id="ingest_bronze",
        python_callable=ingest_bronze,
        doc_md="""
        **Ingestion Bronze**
        Appelle CoinGecko /coins/markets et sauvegarde le JSON brut
        dans MinIO sous crypto-bronze/YYYY/MM/DD/raw.json.
        Retry x3 en cas de timeout ou rate limit (429).
        """,
    )


    # ── TASK 2 — Silver ───────────────────────────────────────────────────────
    task_transform_silver = PythonOperator(
        task_id="transform_silver",
        python_callable=transform_silver,
        doc_md="""
        **Transformation Silver**
        Lit le JSON Bronze, nettoie avec Pandas (snake_case, types, nulls)
        et sauvegarde en Parquet dans crypto-silver/YYYY/MM/DD/clean.parquet.
        Validation des données avant sauvegarde.
        """,
    )


    # ── TASK 3 — Gold ─────────────────────────────────────────────────────────
    task_build_gold = PythonOperator(
        task_id="build_gold_model",
        python_callable=build_gold,
        doc_md="""
        **Modélisation Gold**
        Construit les 5 tables du Snowflake Schema depuis Silver :
        dim_category, dim_platform, dim_crypto, dim_date, fact_crypto_prices.
        Vérifie l'intégrité référentielle avant sauvegarde Parquet.
        """,
    )


    # ── TASK 4 — Snowflake ────────────────────────────────────────────────────
    task_load_snowflake = PythonOperator(
        task_id="load_snowflake",
        python_callable=load_snowflake,
        doc_md="""
        **Chargement Snowflake**
        Crée le schéma si nécessaire (idempotent).
        Charge les dimensions via MERGE, la fact via INSERT avec anti-doublon.
        Valide le nombre de lignes après chargement.
        """,
    )


    # ── DÉPENDANCES ───────────────────────────────────────────────────────────
    task_ingest_bronze >> task_transform_silver >> task_build_gold >> task_load_snowflake