"""
main.py
-------
Point d'entrée du pipeline ETL — E-Commerce Olist.
"""

import logging
from src.extract import load_all_datasets
from src.transform import run_transformations
from src.load import save_to_sqlite, query_sqlite
from src.analyze import run_analysis
from src.validate import validate_raw_data, validate_master_table


# ── Configuration du logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),                         # affichage console
        logging.FileHandler("pipeline.log", mode="w"),  # sauvegarde fichier
    ],
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  PIPELINE ETL — E-COMMERCE OLIST")
    logger.info("=" * 50)

    logger.info("ÉTAPE 1 — EXTRACTION")
    datasets = load_all_datasets()

    logger.info("ÉTAPE 2 — VALIDATION DONNÉES BRUTES")
    validate_raw_data(datasets)

    logger.info("ÉTAPE 3 — TRANSFORMATION")
    df = run_transformations(datasets)

    logger.info("ÉTAPE 4 — VALIDATION TABLE MAÎTRE")
    validate_master_table(df)

    logger.info("ÉTAPE 5 — CHARGEMENT SQL")
    save_to_sqlite(df)

    logger.info("ÉTAPE 6 — TEST REQUÊTE SQL")
    sql = """
        SELECT purchase_year,
               COUNT(DISTINCT order_id) AS nb_commandes,
               ROUND(SUM(revenue), 2)   AS chiffre_affaires
        FROM orders_master
        GROUP BY purchase_year
        ORDER BY purchase_year
    """
    result = query_sqlite(sql)
    logger.info("Résultat requête :\n%s", result.to_string())

    logger.info("ÉTAPE 7 — ANALYSE & VISUALISATION")
    run_analysis()

    logger.info("=" * 50)
    logger.info("PIPELINE TERMINÉ")
    logger.info("=" * 50)