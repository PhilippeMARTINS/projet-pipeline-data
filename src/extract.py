"""
extract.py
----------
Module d'extraction : chargement des fichiers CSV Olist en DataFrames Pandas.
"""

import pandas as pd
from pathlib import Path


# Chemin vers les données brutes
RAW_DATA_PATH = Path("data/raw")


def load_all_datasets() -> dict[str, pd.DataFrame]:
    """
    Charge tous les fichiers CSV du dataset Olist.

    Returns:
        dict: Dictionnaire {nom_table: DataFrame}
    """
    fichiers = {
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "products": "olist_products_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "geolocation": "olist_geolocation_dataset.csv",
        "category_translation": "product_category_name_translation.csv",
    }

    datasets = {}

    for nom, fichier in fichiers.items():
        chemin = RAW_DATA_PATH / fichier
        datasets[nom] = pd.read_csv(chemin)
        print(f"✅ {nom} chargé — {datasets[nom].shape[0]} lignes, {datasets[nom].shape[1]} colonnes")

    return datasets


if __name__ == "__main__":
    datasets = load_all_datasets()