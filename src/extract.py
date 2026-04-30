"""
extract.py
----------
Module d'extraction : chargement des fichiers CSV Olist en DataFrames Pandas.
"""

import logging
import pandas as pd
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

RAW_DATA_PATH = Path("data/raw")

FICHIERS = {
    "orders":               "olist_orders_dataset.csv",
    "order_items":          "olist_order_items_dataset.csv",
    "products":             "olist_products_dataset.csv",
    "customers":            "olist_customers_dataset.csv",
    "sellers":              "olist_sellers_dataset.csv",
    "payments":             "olist_order_payments_dataset.csv",
    "reviews":              "olist_order_reviews_dataset.csv",
    "geolocation":          "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def load_all_datasets() -> dict[str, pd.DataFrame]:
    """
    Charge tous les fichiers CSV du dataset Olist.

    Returns:
        dict: Dictionnaire {nom_table: DataFrame}

    Raises:
        FileNotFoundError: Si un fichier CSV est absent de data/raw/
    """
    logger.info("Chargement des datasets Olist depuis '%s'", RAW_DATA_PATH)
    datasets = {}

    for nom, fichier in FICHIERS.items():
        chemin = RAW_DATA_PATH / fichier
        if not chemin.exists():
            logger.error("Fichier manquant : %s", chemin)
            raise FileNotFoundError(f"Fichier introuvable : {chemin}")
        datasets[nom] = pd.read_csv(chemin)
        logger.info(
            "  %-25s : %d lignes, %d colonnes",
            nom,
            datasets[nom].shape[0],
            datasets[nom].shape[1],
        )

    logger.info("%d datasets chargés avec succès", len(datasets))
    return datasets


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    datasets = load_all_datasets()