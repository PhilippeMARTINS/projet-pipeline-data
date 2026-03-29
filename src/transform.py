"""
transform.py
------------
Module de transformation : nettoyage, jointures et calcul des KPIs e-commerce.
"""

import pandas as pd


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie la table orders :
    - Conversion des colonnes de dates en datetime
    - Suppression des commandes sans date d'achat
    """
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]

    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    # On garde uniquement les commandes avec une date d'achat valide
    orders = orders.dropna(subset=["order_purchase_timestamp"])

    print(f"✅ orders nettoyé — {orders.shape[0]} lignes conservées")
    return orders


def build_master_table(datasets: dict) -> pd.DataFrame:
    """
    Construit la table principale en joignant :
    orders + order_items + products + customers + category_translation

    Returns:
        pd.DataFrame: Table maître enrichie
    """
    orders = datasets["orders"]
    items = datasets["order_items"]
    products = datasets["products"]
    customers = datasets["customers"]
    translation = datasets["category_translation"]

    # Jointure orders + items
    df = orders.merge(items, on="order_id", how="inner")

    # Jointure avec products
    df = df.merge(products, on="product_id", how="left")

    # Jointure avec la traduction des catégories
    df = df.merge(translation, on="product_category_name", how="left")

    # Jointure avec customers
    df = df.merge(customers, on="customer_id", how="left")

    print(f"✅ Table maître construite — {df.shape[0]} lignes, {df.shape[1]} colonnes")
    return df


def compute_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les KPIs e-commerce sur la table maître :
    - Chiffre d'affaires total par commande
    - Délai de livraison en jours
    - Mois et année d'achat
    """
    # Chiffre d'affaires = prix + frais de port
    df["revenue"] = df["price"] + df["freight_value"]

    # Délai de livraison en jours
    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days

    # Extraction du mois et de l'année pour les analyses temporelles
    df["purchase_month"] = df["order_purchase_timestamp"].dt.to_period("M")
    df["purchase_year"] = df["order_purchase_timestamp"].dt.year

    print("✅ KPIs calculés : revenue, delivery_days, purchase_month, purchase_year")
    return df


def run_transformations(datasets: dict) -> pd.DataFrame:
    """
    Orchestre toutes les transformations dans l'ordre.

    Returns:
        pd.DataFrame: Table finale prête pour l'analyse
    """
    datasets["orders"] = clean_orders(datasets["orders"])
    df = build_master_table(datasets)
    df = compute_kpis(df)
    return df