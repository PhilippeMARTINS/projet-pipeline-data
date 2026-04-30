"""
load.py
-------
Module de chargement : sauvegarde de la table maître dans une base SQLite
et exécution de requêtes analytiques.
"""

import logging
import sqlite3
from pathlib import Path

import pandas as pd


# ── Configuration ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

DB_PATH = Path("data/processed/ecommerce.db")


def save_to_sqlite(df: pd.DataFrame, table_name: str = "orders_master") -> None:
    """
    Sauvegarde un DataFrame dans la base SQLite.

    La table est remplacée si elle existe déjà (REPLACE).
    La colonne purchase_month est convertie en string car SQLite
    ne supporte pas le type Period de Pandas.

    Args:
        df:         Table maître à sauvegarder
        table_name: Nom de la table SQL (défaut : orders_master)
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = df.copy()
    df["purchase_month"] = df["purchase_month"].astype(str)

    conn = sqlite3.connect(DB_PATH)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

    logger.info(
        "%d lignes sauvegardées dans la table '%s' (%s)",
        len(df), table_name, DB_PATH,
    )


def query_sqlite(sql: str) -> pd.DataFrame:
    """
    Exécute une requête SQL sur la base SQLite et retourne un DataFrame.

    Args:
        sql: Requête SQL à exécuter

    Returns:
        pd.DataFrame: Résultat de la requête

    Raises:
        sqlite3.Error: Si la requête SQL est invalide
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sql_test = """
        SELECT purchase_year,
               COUNT(DISTINCT order_id) AS nb_commandes,
               ROUND(SUM(revenue), 2)   AS chiffre_affaires
        FROM orders_master
        GROUP BY purchase_year
        ORDER BY purchase_year
    """
    result = query_sqlite(sql_test)
    logger.info("Résultat :\n%s", result.to_string())