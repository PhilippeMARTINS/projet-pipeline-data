"""
app.py
------
Dashboard Streamlit — Analyse des ventes e-commerce Olist.
Lancer avec : streamlit run app.py
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import streamlit as st
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DB_PATH = Path("data/processed/ecommerce.db")
sns.set_theme(style="whitegrid")

st.set_page_config(
    page_title="E-Commerce Dashboard — Olist",
    page_icon="🛒",
    layout="wide",
)


# ── Helpers ────────────────────────────────────────────────────────────────────
@st.cache_data
def query(sql: str) -> pd.DataFrame:
    """Exécute une requête SQL et retourne un DataFrame (résultat mis en cache)."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df


@st.cache_data
def get_years() -> list[int]:
    df = query("SELECT DISTINCT purchase_year FROM orders_master ORDER BY purchase_year")
    return df["purchase_year"].tolist()


@st.cache_data
def get_categories() -> list[str]:
    df = query("""
        SELECT DISTINCT product_category_name_english
        FROM orders_master
        WHERE product_category_name_english IS NOT NULL
        ORDER BY product_category_name_english
    """)
    return df["product_category_name_english"].tolist()


# ── Sidebar — Filtres ──────────────────────────────────────────────────────────
st.sidebar.title("🔧 Filtres")

years = get_years()
selected_years = st.sidebar.multiselect(
    "Année(s)",
    options=years,
    default=years,
)

categories = get_categories()
selected_cats = st.sidebar.multiselect(
    "Catégorie(s) de produits",
    options=categories,
    default=categories[:10],  # Top 10 par défaut pour la lisibilité
)

st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Astuce** : laisse toutes les catégories vides pour tout afficher.")

# Gestion du cas "aucune sélection"
if not selected_years:
    selected_years = years
if not selected_cats:
    selected_cats = categories

years_sql   = ", ".join(str(y) for y in selected_years)
cats_sql    = ", ".join(f"'{c}'" for c in selected_cats)


# ── Titre ─────────────────────────────────────────────────────────────────────
st.title("🛒 E-Commerce Sales Dashboard — Olist")
st.caption("Pipeline ETL · Python · Pandas · SQLite · Streamlit")
st.markdown("---")


# ── KPIs globaux ───────────────────────────────────────────────────────────────
kpi_sql = f"""
    SELECT
        COUNT(DISTINCT order_id)              AS nb_commandes,
        ROUND(SUM(revenue), 2)                AS ca_total,
        ROUND(AVG(delivery_days), 1)          AS delai_moyen,
        COUNT(DISTINCT customer_unique_id)    AS nb_clients
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
"""
kpi = query(kpi_sql).iloc[0]

col1, col2, col3, col4 = st.columns(4)
col1.metric("🧾 Commandes",      f"{int(kpi['nb_commandes']):,}".replace(",", " "))
col2.metric("💰 Chiffre d'affaires", f"{kpi['ca_total']:,.0f} €".replace(",", " "))
col3.metric("🚚 Délai moyen",    f"{kpi['delai_moyen']} jours")
col4.metric("👥 Clients uniques", f"{int(kpi['nb_clients']):,}".replace(",", " "))

st.markdown("---")


# ── Graphique 1 — CA mensuel ───────────────────────────────────────────────────
st.subheader("📈 Chiffre d'affaires mensuel")

ca_sql = f"""
    SELECT purchase_month,
           ROUND(SUM(revenue), 2) AS ca_mensuel
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY purchase_month
    ORDER BY purchase_month
"""
df_ca = query(ca_sql)

fig1, ax1 = plt.subplots(figsize=(14, 4))
ax1.plot(df_ca["purchase_month"], df_ca["ca_mensuel"],
         marker="o", color="#2563EB", linewidth=2)
ax1.fill_between(range(len(df_ca)), df_ca["ca_mensuel"], alpha=0.1, color="#2563EB")
ax1.set_xticks(range(len(df_ca)))
ax1.set_xticklabels(df_ca["purchase_month"], rotation=45, ha="right", fontsize=8)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
ax1.set_xlabel("Mois")
ax1.set_ylabel("CA (k€)")
plt.tight_layout()
st.pyplot(fig1)
plt.close()

st.markdown("---")


# ── Graphique 2 — Top catégories ──────────────────────────────────────────────
st.subheader("🏆 Top catégories par chiffre d'affaires")

n_top = st.slider("Nombre de catégories à afficher", min_value=5, max_value=20, value=10)

top_sql = f"""
    SELECT product_category_name_english AS categorie,
           ROUND(SUM(revenue), 2)        AS ca
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY categorie
    ORDER BY ca DESC
    LIMIT {n_top}
"""
df_top = query(top_sql)

fig2, ax2 = plt.subplots(figsize=(10, max(4, n_top * 0.45)))
ax2.barh(df_top["categorie"][::-1], df_top["ca"][::-1], color="#2563EB")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
ax2.set_xlabel("CA (k€)")
plt.tight_layout()
st.pyplot(fig2)
plt.close()

st.markdown("---")


# ── Graphique 3 — Distribution des délais ─────────────────────────────────────
st.subheader("🚚 Distribution des délais de livraison")

delai_sql = f"""
    SELECT delivery_days
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
      AND delivery_days IS NOT NULL
      AND delivery_days BETWEEN 0 AND 60
"""
df_delai = query(delai_sql)

fig3, ax3 = plt.subplots(figsize=(10, 4))
ax3.hist(df_delai["delivery_days"], bins=40, color="#2563EB", edgecolor="white", alpha=0.85)
ax3.axvline(df_delai["delivery_days"].mean(), color="#DC2626", linestyle="--", linewidth=2,
            label=f"Moyenne : {df_delai['delivery_days'].mean():.1f} jours")
ax3.set_xlabel("Jours")
ax3.set_ylabel("Nombre de commandes")
ax3.legend()
plt.tight_layout()
st.pyplot(fig3)
plt.close()

st.markdown("---")


# ── Section SQL dynamique ──────────────────────────────────────────────────────
st.subheader("🧮 Requête SQL personnalisée")
st.caption("Interroge directement la table `orders_master` avec ta propre requête.")

default_sql = """SELECT purchase_year,
       COUNT(DISTINCT order_id) AS nb_commandes,
       ROUND(SUM(revenue), 2)   AS chiffre_affaires
FROM orders_master
GROUP BY purchase_year
ORDER BY purchase_year"""

custom_sql = st.text_area("Requête SQL", value=default_sql, height=150)

if st.button("▶️ Exécuter"):
    try:
        df_custom = query(custom_sql)
        st.success(f"{len(df_custom)} ligne(s) retournée(s)")
        st.dataframe(df_custom, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur SQL : {e}")

st.markdown("---")
st.caption("Projet réalisé par **Philippe Morais Martins** · M2 Data Engineering · Paris Ynov Campus")
