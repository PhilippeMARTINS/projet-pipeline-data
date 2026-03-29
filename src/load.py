"""
load.py
-------
Module de chargement : sauvegarde de la table maître dans une base SQLite.
"""

import sqlite3
import pandas as pd
from pathlib import Path


DB_PATH = Path("data/processed/ecommerce.db")


def save_to_sqlite(df: pd.DataFrame, table_name: str = "orders_master") -> None:
    """
    Sauvegarde un DataFrame dans une base SQLite.

    Args:
        df: Table maître à sauvegarder
        table_name: Nom de la table SQL (défaut: orders_master)
    """
    # Conversion de purchase_month en string (SQLite ne supporte pas Period)
    df = df.copy()
    df["purchase_month"] = df["purchase_month"].astype(str)

    conn = sqlite3.connect(DB_PATH)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

    print(f"✅ {len(df)} lignes sauvegardées dans '{table_name}' ({DB_PATH})")


def query_sqlite(sql: str) -> pd.DataFrame:
    """
    Exécute une requête SQL sur la base et retourne un DataFrame.

    Args:
        sql: Requête SQL à exécuter

    Returns:
        pd.DataFrame: Résultat de la requête
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df