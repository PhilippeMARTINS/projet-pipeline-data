"""
tests/test_transform.py
-----------------------
Tests unitaires pour le module src/transform.py (Projet 1 — Olist).
Lancer avec : pytest tests/ -v
"""

import pandas as pd
import numpy as np
import pytest
from src.transform import clean_orders, build_master_table, compute_kpis


# ── Fixtures : mini-datasets réutilisables ─────────────────────────────────────

@pytest.fixture
def sample_orders():
    """Table orders minimale avec des cas normaux et des cas limites."""
    return pd.DataFrame({
        "order_id":                      ["o1", "o2", "o3"],
        "customer_id":                   ["c1", "c2", "c3"],
        "order_status":                  ["delivered", "delivered", "canceled"],
        "order_purchase_timestamp":      ["2017-03-15 10:00:00", None, "2018-06-01 09:00:00"],
        "order_approved_at":             ["2017-03-15 11:00:00", None, "2018-06-01 10:00:00"],
        "order_delivered_carrier_date":  ["2017-03-16 08:00:00", None, "2018-06-03 08:00:00"],
        "order_delivered_customer_date": ["2017-03-20 14:00:00", None, "2018-06-08 14:00:00"],
        "order_estimated_delivery_date": ["2017-03-25 00:00:00", None, "2018-06-15 00:00:00"],
    })


@pytest.fixture
def sample_datasets(sample_orders):
    """
    Ensemble minimal de datasets pour tester build_master_table et compute_kpis.
    """
    orders = sample_orders.copy()
    # Simulation du nettoyage déjà effectué (dates converties, NaT supprimé)
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    orders = orders.dropna(subset=["order_purchase_timestamp"])

    order_items = pd.DataFrame({
        "order_id":    ["o1", "o1", "o3"],
        "product_id":  ["p1", "p2", "p1"],
        "price":       [100.0, 50.0, 80.0],
        "freight_value": [10.0, 5.0, 8.0],
    })

    products = pd.DataFrame({
        "product_id":            ["p1", "p2"],
        "product_category_name": ["eletronicos", "beleza_saude"],
    })

    customers = pd.DataFrame({
        "customer_id":        ["c1", "c3"],
        "customer_unique_id": ["u1", "u3"],
        "customer_city":      ["São Paulo", "Rio de Janeiro"],
        "customer_state":     ["SP", "RJ"],
    })

    translation = pd.DataFrame({
        "product_category_name":         ["eletronicos", "beleza_saude"],
        "product_category_name_english": ["electronics", "health_beauty"],
    })

    return {
        "orders":               orders,
        "order_items":          order_items,
        "products":             products,
        "customers":            customers,
        "category_translation": translation,
    }


# ── Tests : clean_orders ───────────────────────────────────────────────────────

class TestCleanOrders:

    def test_supprime_lignes_sans_date_achat(self, sample_orders):
        """Une ligne avec order_purchase_timestamp=None doit être supprimée."""
        result = clean_orders(sample_orders)
        assert len(result) == 2, "La ligne sans date d'achat aurait dû être supprimée"

    def test_dates_converties_en_datetime(self, sample_orders):
        """Toutes les colonnes de dates doivent être de type datetime64."""
        result = clean_orders(sample_orders)
        date_cols = [
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]
        for col in date_cols:
            assert pd.api.types.is_datetime64_any_dtype(result[col]), \
                f"La colonne {col} devrait être datetime64"

    def test_retourne_dataframe(self, sample_orders):
        """clean_orders doit retourner un DataFrame."""
        result = clean_orders(sample_orders)
        assert isinstance(result, pd.DataFrame)

    def test_toutes_lignes_valides_conservees(self, sample_orders):
        """Les lignes avec une date valide doivent toutes être conservées."""
        result = clean_orders(sample_orders)
        assert result["order_purchase_timestamp"].isna().sum() == 0


# ── Tests : build_master_table ─────────────────────────────────────────────────

class TestBuildMasterTable:

    def test_retourne_dataframe(self, sample_datasets):
        result = build_master_table(sample_datasets)
        assert isinstance(result, pd.DataFrame)

    def test_colonnes_essentielles_presentes(self, sample_datasets):
        """Les colonnes clés issues des jointures doivent être présentes."""
        result = build_master_table(sample_datasets)
        colonnes_attendues = [
            "order_id", "customer_id", "product_id",
            "price", "freight_value",
            "product_category_name_english",
        ]
        for col in colonnes_attendues:
            assert col in result.columns, f"Colonne manquante : {col}"

    def test_nombre_lignes_coherent(self, sample_datasets):
        """
        La jointure orders × order_items doit donner autant de lignes
        qu'il y a d'items pour les orders valides.
        """
        result = build_master_table(sample_datasets)
        # o1 a 2 items, o3 a 1 item → 3 lignes attendues
        assert len(result) == 3

    def test_traduction_categorie_appliquee(self, sample_datasets):
        """Les catégories doivent être traduites en anglais."""
        result = build_master_table(sample_datasets)
        assert "electronics" in result["product_category_name_english"].values


# ── Tests : compute_kpis ───────────────────────────────────────────────────────

class TestComputeKpis:

    @pytest.fixture
    def master_df(self, sample_datasets):
        """Table maître prête pour compute_kpis."""
        return build_master_table(sample_datasets)

    def test_colonne_revenue_creee(self, master_df):
        """La colonne revenue doit être créée."""
        result = compute_kpis(master_df)
        assert "revenue" in result.columns

    def test_revenue_egal_prix_plus_fret(self, master_df):
        """revenue = price + freight_value pour chaque ligne."""
        result = compute_kpis(master_df)
        expected = result["price"] + result["freight_value"]
        pd.testing.assert_series_equal(
            result["revenue"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    def test_colonne_delivery_days_creee(self, master_df):
        """La colonne delivery_days doit être créée."""
        result = compute_kpis(master_df)
        assert "delivery_days" in result.columns

    def test_delivery_days_positif_ou_nan(self, master_df):
        """Les délais de livraison valides doivent être positifs ou nuls."""
        result = compute_kpis(master_df)
        valides = result["delivery_days"].dropna()
        assert (valides >= 0).all(), "Des délais négatifs ont été détectés"

    def test_purchase_month_type_period(self, master_df):
        """purchase_month doit être de type Period (fréquence mensuelle)."""
        result = compute_kpis(master_df)
        assert hasattr(result["purchase_month"].dtype, "freq"), \
            "purchase_month devrait être un PeriodIndex mensuel"

    def test_purchase_year_type_entier(self, master_df):
        """purchase_year doit contenir des entiers."""
        result = compute_kpis(master_df)
        assert pd.api.types.is_integer_dtype(result["purchase_year"])

    def test_valeurs_purchase_year_coherentes(self, master_df):
        """Les années doivent être dans la plage du dataset Olist (2016-2018)."""
        result = compute_kpis(master_df)
        annees = result["purchase_year"].dropna().unique()
        for annee in annees:
            assert 2016 <= annee <= 2019, f"Année inattendue : {annee}"
