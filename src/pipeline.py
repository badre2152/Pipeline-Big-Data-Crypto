"""
pipeline.py — Orchestration manuelle
=====================================
Point d'entrée pour lancer le pipeline complet sans Airflow.
Utile en développement, tests, et démonstration.

Usage :
    python -m src.pipeline                        # run pour aujourd'hui
    python -m src.pipeline --date 2025-01-15      # run pour une date précise
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from src.ingestion.ingest_bronze import ingest_bronze
from src.transformation.transform_silver import transform_silver
from src.modeling.build_gold import build_gold
from src.loading.load_snowflake import load_snowflake

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pipeline")


STEPS = {
    "bronze":    ingest_bronze,
    "silver":    transform_silver,
    "gold":      build_gold,
    "snowflake": load_snowflake,
}


def parse_args():
    parser = argparse.ArgumentParser(description="Crypto Pipeline — orchestration manuelle")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date du run au format YYYY-MM-DD (défaut: aujourd'hui UTC)",
    )
    parser.add_argument(
        "--steps",
        nargs="+",
        choices=list(STEPS.keys()),
        default=list(STEPS.keys()),
        help="Étapes à exécuter (défaut: toutes)",
    )
    return parser.parse_args()


def run(date: datetime = None, steps: list[str] = None) -> None:
    if date is None:
        date = datetime.now(timezone.utc)
    if steps is None:
        steps = list(STEPS.keys())

    logger.info(f"{'='*55}")
    logger.info(f"  CRYPTO PIPELINE — {date.strftime('%Y-%m-%d')} UTC")
    logger.info(f"  Steps : {' >> '.join(steps)}")
    logger.info(f"{'='*55}")

    for step_name in steps:
        fn = STEPS[step_name]
        logger.info(f"[{step_name.upper()}] Starting...")

        try:
            fn(date=date) if step_name != "bronze" else fn()
            logger.info(f"[{step_name.upper()}] Done ✓")

        except Exception as e:
            logger.error(f"[{step_name.upper()}] FAILED — {e}")
            logger.error("Pipeline stopped. Fix the error and re-run.")
            sys.exit(1)

    logger.info(f"{'='*55}")
    logger.info("  PIPELINE COMPLETE ✓")
    logger.info(f"{'='*55}")


if __name__ == "__main__":
    args = parse_args()

    run_date = (
        datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.date
        else None
    )

    run(date=run_date, steps=args.steps)