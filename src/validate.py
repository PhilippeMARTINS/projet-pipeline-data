"""
validate.py
-----------
Validation de la qualité des données.
Appelé automatiquement par main.py après l'extraction et la transformation.
"""

import logging
import pandas as pd


logger = logging.getLogger(__name__)


def _check(label: str, condition: bool, detail: str = "") -> bool:
    """
    Logue le résultat d'un check et retourne le succès.

    Args:
        label:     Libellé du check
        condition: True si le check passe
        detail:    Message complémentaire en cas d'échec

    Returns:
        bool: True si le check passe, False sinon
    """
    if condition:
        logger.info("    [OK] %s", label)
    else:
        msg = f"    [KO] {label}"
        if detail:
            msg += f" -- {detail}"
        logger.warning(msg)
    return condition


def validate_raw_data(datasets: dict) -> bool:
    """
    Valide les données brutes après extraction.

    Args:
        datasets: Dictionnaire des DataFrames chargés par extract.py

    Returns:
        bool: True si toutes les validations passent, False sinon
    """
    logger.info("Validation des données brutes :")
    all_passed = True

    # ── orders ────────────────────────────────────────────────────────────────
    logger.info("  [orders]")
    orders = datasets["orders"]
    valid_statuses = {
        "delivered", "shipped", "canceled", "invoiced",
        "processing", "unavailable", "approved", "created",
    }
    all_passed &= _check("order_id sans valeurs nulles", orders["order_id"].notna().all())
    all_passed &= _check("customer_id sans valeurs nulles", orders["customer_id"].notna().all())
    all_passed &= _check(
        "order_status dans les valeurs attendues",
        orders["order_status"].isin(valid_statuses).all(),
        f"valeurs inattendues : {orders[~orders['order_status'].isin(valid_statuses)]['order_status'].unique().tolist()}",
    )
    all_passed &= _check(
        "order_purchase_timestamp sans valeurs nulles",
        orders["order_purchase_timestamp"].notna().all(),
    )

    # ── order_items ───────────────────────────────────────────────────────────
    logger.info("  [order_items]")
    items = datasets["order_items"]
    all_passed &= _check("order_id sans valeurs nulles", items["order_id"].notna().all())
    all_passed &= _check("product_id sans valeurs nulles", items["product_id"].notna().all())
    all_passed &= _check(
        "price entre 0 et 10 000",
        items["price"].between(0, 10_000).all(),
        f"min={items['price'].min():.2f}, max={items['price'].max():.2f}",
    )
    all_passed &= _check(
        "freight_value entre 0 et 1 000",
        items["freight_value"].between(0, 1_000).all(),
        f"min={items['freight_value'].min():.2f}, max={items['freight_value'].max():.2f}",
    )

    # ── reviews ───────────────────────────────────────────────────────────────
    logger.info("  [reviews]")
    reviews = datasets["reviews"]
    all_passed &= _check("order_id sans valeurs nulles", reviews["order_id"].notna().all())
    valid_scores = reviews["review_score"].dropna()
    pct_valid = valid_scores.between(1, 5).mean()
    all_passed &= _check(
        "review_score entre 1 et 5 (tolerance 5% nulls)",
        pct_valid >= 0.95,
        f"{pct_valid * 100:.1f}% de valeurs valides",
    )

    if all_passed:
        logger.info("Validation donnees brutes : toutes les verifications sont passees [OK]")
    else:
        logger.warning("Validation donnees brutes : certains checks ont echoue [KO]")

    return all_passed


def validate_master_table(df: pd.DataFrame) -> bool:
    """
    Valide la table maître après transformation.

    Args:
        df: DataFrame issu de run_transformations()

    Returns:
        bool: True si toutes les validations passent, False sinon
    """
    logger.info("Validation de la table maitre :")
    all_passed = True

    colonnes_attendues = [
        "order_id", "customer_id", "product_id",
        "price", "freight_value", "revenue",
        "delivery_days", "purchase_month", "purchase_year",
        "product_category_name_english",
    ]

    for col in colonnes_attendues:
        all_passed &= _check(f"colonne '{col}' presente", col in df.columns)

    if "revenue" in df.columns:
        all_passed &= _check(
            "revenue positif",
            (df["revenue"] >= 0).all(),
            f"min={df['revenue'].min():.2f}",
        )

    if "delivery_days" in df.columns:
        invalid = df["delivery_days"].dropna()
        all_passed &= _check(
            "delivery_days positif ou nul",
            (invalid >= 0).all(),
            f"valeurs negatives : {(invalid < 0).sum()}",
        )

    all_passed &= _check(
        "aucune ligne dupliquee",
        df.duplicated().sum() == 0,
        f"{df.duplicated().sum()} doublons detectes",
    )

    if all_passed:
        logger.info("Validation table maitre : toutes les verifications sont passees [OK]")
    else:
        logger.warning("Validation table maitre : certains checks ont echoue [KO]")

    return all_passed