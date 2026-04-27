"""
validate.py
-----------
Validation de la qualité des données avec Great Expectations.
Appelé automatiquement par main.py après l'extraction et la transformation.
"""

import pandas as pd


def _check(label: str, condition: bool, detail: str = "") -> bool:
    """Affiche le résultat d'un check et retourne le succès."""
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}{' — ' + detail if detail else ''}")
    return condition


def validate_raw_data(datasets: dict) -> bool:
    """
    Valide les données brutes après extraction.

    Args:
        datasets: dictionnaire des DataFrames chargés par extract.py

    Returns:
        bool: True si toutes les validations passent, False sinon
    """
    print("\n=== VALIDATION DONNÉES BRUTES ===")
    all_passed = True

    # ── Validation orders ─────────────────────────────────────────────────────
    print("orders :")
    orders = datasets["orders"]
    valid_statuses = {"delivered", "shipped", "canceled", "invoiced",
                      "processing", "unavailable", "approved", "created"}

    all_passed &= _check(
        "order_id sans valeurs nulles",
        orders["order_id"].notna().all()
    )
    all_passed &= _check(
        "customer_id sans valeurs nulles",
        orders["customer_id"].notna().all()
    )
    all_passed &= _check(
        "order_status dans les valeurs attendues",
        orders["order_status"].isin(valid_statuses).all(),
        f"valeurs inattendues : {orders[~orders['order_status'].isin(valid_statuses)]['order_status'].unique().tolist()}"
    )
    all_passed &= _check(
        "order_purchase_timestamp sans valeurs nulles",
        orders["order_purchase_timestamp"].notna().all()
    )

    # ── Validation order_items ────────────────────────────────────────────────
    print("order_items :")
    items = datasets["order_items"]

    all_passed &= _check(
        "order_id sans valeurs nulles",
        items["order_id"].notna().all()
    )
    all_passed &= _check(
        "product_id sans valeurs nulles",
        items["product_id"].notna().all()
    )
    all_passed &= _check(
        "price entre 0 et 10 000",
        items["price"].between(0, 10000).all(),
        f"min={items['price'].min():.2f}, max={items['price'].max():.2f}"
    )
    all_passed &= _check(
        "freight_value entre 0 et 1 000",
        items["freight_value"].between(0, 1000).all(),
        f"min={items['freight_value'].min():.2f}, max={items['freight_value'].max():.2f}"
    )

    # ── Validation reviews ────────────────────────────────────────────────────
    print("reviews :")
    reviews = datasets["reviews"]

    all_passed &= _check(
        "order_id sans valeurs nulles",
        reviews["order_id"].notna().all()
    )
    valid_scores = reviews["review_score"].dropna()
    pct_valid = valid_scores.between(1, 5).mean()
    all_passed &= _check(
        "review_score entre 1 et 5 (tolérance 5% nulls)",
        pct_valid >= 0.95,
        f"{pct_valid*100:.1f}% de valeurs valides"
    )

    return all_passed


def validate_master_table(df: pd.DataFrame) -> bool:
    """
    Valide la table maître après transformation.

    Args:
        df: DataFrame orders_master

    Returns:
        bool: True si toutes les validations passent, False sinon
    """
    print("\n=== VALIDATION TABLE MAÎTRE ===")
    all_passed = True

    # Colonnes critiques non nulles
    all_passed &= _check(
        "order_id sans valeurs nulles",
        df["order_id"].notna().all()
    )
    all_passed &= _check(
        "revenue sans valeurs nulles",
        df["revenue"].notna().all()
    )

    # Revenue positif
    all_passed &= _check(
        "revenue toujours positif",
        (df["revenue"] > 0).all(),
        f"min={df['revenue'].min():.2f}"
    )

    # Prix positif
    all_passed &= _check(
        "price entre 0 et 10 000",
        df["price"].between(0, 10000).all(),
        f"min={df['price'].min():.2f}, max={df['price'].max():.2f}"
    )

    # Delivery days avec tolérance 1%
    valid_delivery = df["delivery_days"].dropna()
    pct_valid_delivery = valid_delivery.between(1, 365).mean()
    all_passed &= _check(
        "delivery_days entre 1 et 365 (tolérance 1%)",
        pct_valid_delivery >= 0.99,
        f"{pct_valid_delivery*100:.1f}% de valeurs valides"
    )

    # Review score avec tolérance 5%
    valid_reviews = df["review_score"].dropna()
    pct_valid_reviews = valid_reviews.between(1, 5).mean()
    all_passed &= _check(
        "review_score entre 1 et 5 (tolérance 5% nulls)",
        pct_valid_reviews >= 0.95,
        f"{pct_valid_reviews*100:.1f}% de valeurs valides"
    )

    # Max 5% de catégories nulles
    pct_cat_not_null = df["product_category_name_english"].notna().mean()
    all_passed &= _check(
        "product_category_name_english (max 5% nulls)",
        pct_cat_not_null >= 0.95,
        f"{pct_cat_not_null*100:.1f}% de valeurs non nulles"
    )

    # Purchase year dans les années du dataset
    valid_years = {2016, 2017, 2018}
    all_passed &= _check(
        "purchase_year dans [2016, 2017, 2018]",
        df["purchase_year"].isin(valid_years).all(),
        f"valeurs inattendues : {df[~df['purchase_year'].isin(valid_years)]['purchase_year'].unique().tolist()}"
    )

    if all_passed:
        print("\n✅ Toutes les validations sont passées !")
    else:
        print("\n⚠️ Certaines validations ont échoué — vérifiez les données.")

    return all_passed