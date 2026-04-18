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
import plotly.graph_objects as go

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

# ── Top 10 catégories par CA (défaut intelligent) ─────────────────────────────
@st.cache_data
def get_top10_categories() -> list[str]:
    """Retourne les 10 catégories avec le plus grand CA."""
    df = query("""
        SELECT product_category_name_english AS cat,
               SUM(revenue) AS ca
        FROM orders_master
        WHERE product_category_name_english IS NOT NULL
        GROUP BY cat
        ORDER BY ca DESC
        LIMIT 10
    """)
    return df["cat"].tolist()

# ── Sidebar — Filtres ──────────────────────────────────────────────────────────
st.sidebar.title("🔧 Filtres")

years = get_years()
categories = get_categories()
top10_cats = get_top10_categories()

# Bouton réinitialisation
if st.sidebar.button("🔄 Réinitialiser les filtres"):
    st.session_state["selected_years"] = years
    st.session_state["selected_cats"] = top10_cats

# Filtre années
selected_years = st.sidebar.multiselect(
    "Année(s)",
    options=years,
    default=years,
    key="selected_years",
)

# Filtre catégories
selected_cats = st.sidebar.multiselect(
    "Catégorie(s) de produits",
    options=categories,
    default=top10_cats,
    key="selected_cats",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**💡 Astuce** : laisse vide pour tout afficher.")

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


# ── Graphique 1 — CA mensuel + volume de commandes ────────────────────────────
st.subheader("📈 Chiffre d'affaires et volume de commandes mensuel")

ca_sql = f"""
    SELECT purchase_month,
           ROUND(SUM(revenue), 2)        AS ca_mensuel,
           COUNT(DISTINCT order_id)      AS nb_commandes
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY purchase_month
    ORDER BY purchase_month
"""
df_ca = query(ca_sql)

fig1, ax1 = plt.subplots(figsize=(14, 4))

# ── Axe gauche : CA ───────────────────────────────────────────────────────────
ax1.plot(range(len(df_ca)), df_ca["ca_mensuel"],
         marker="o", color="#2563EB", linewidth=2, label="CA mensuel", zorder=3)
ax1.fill_between(range(len(df_ca)), df_ca["ca_mensuel"],
                 alpha=0.1, color="#2563EB")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
ax1.set_ylabel("CA (k€)", color="#2563EB")
ax1.tick_params(axis="y", labelcolor="#2563EB")

# ── Axe droit : volume de commandes ──────────────────────────────────────────
ax2 = ax1.twinx()
ax2.plot(range(len(df_ca)), df_ca["nb_commandes"],
         marker="s", color="#16A34A", linewidth=1.5,
         linestyle="--", label="Nb commandes", zorder=2)
ax2.set_ylabel("Nombre de commandes", color="#16A34A")
ax2.tick_params(axis="y", labelcolor="#16A34A")

# ── Zone de croissance ────────────────────────────────────────────────────────
idx_debut = df_ca[df_ca["purchase_month"] == "2017-01"].index
idx_pic   = df_ca[df_ca["purchase_month"] == "2017-11"].index
if len(idx_debut) and len(idx_pic):
    i_debut = df_ca.index.get_loc(idx_debut[0])
    i_pic   = df_ca.index.get_loc(idx_pic[0])
    ax1.axvspan(i_debut, i_pic, alpha=0.07, color="#16A34A",
                label="Période de croissance (jan–nov 2017)")

# ── Annotation Black Friday ───────────────────────────────────────────────────
idx_bf = df_ca[df_ca["purchase_month"] == "2017-11"].index
if len(idx_bf):
    i_bf   = df_ca.index.get_loc(idx_bf[0])
    val_bf = df_ca.loc[idx_bf[0], "ca_mensuel"]
    ax1.annotate(
        f"Pic Black Friday\n{val_bf/1000:.0f}k€",
        xy=(i_bf, val_bf),
        xytext=(i_bf - 4, val_bf * 0.75),
        fontsize=9, color="#DC2626",
        arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#DC2626", alpha=0.85),
    )

# ── Légende combinée des deux axes ────────────────────────────────────────────
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="upper left")

ax1.set_xticks(range(len(df_ca)))
ax1.set_xticklabels(df_ca["purchase_month"], rotation=45, ha="right", fontsize=8)
ax1.set_xlabel("Mois")
plt.tight_layout()
st.pyplot(fig1)
plt.close()

st.markdown("---")


# ── Graphique 2 — Top catégories ──────────────────────────────────────────────
st.subheader("🏆 Top catégories par chiffre d'affaires")

n_top = st.slider(
    "Nombre de catégories à afficher",
    min_value=1,
    max_value=len(selected_cats) if selected_cats else len(categories),
    value=min(10, len(selected_cats) if selected_cats else 10),
)

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

fig2, ax2 = plt.subplots(figsize=(10, max(4, n_top * 0.5)))
bars = ax2.barh(df_top["categorie"][::-1], df_top["ca"][::-1],
                color="#2563EB", alpha=0.85)

seuil = df_top["ca"].max() * 0.15
for bar, val in zip(bars, df_top["ca"][::-1]):
    if bar.get_width() >= seuil:
        ax2.text(
            bar.get_width() - df_top["ca"].max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val/1000:.0f}k€",
            va="center", ha="right", fontsize=9,
            color="white", fontweight="bold",
        )
    else:
        ax2.text(
            bar.get_width() + df_top["ca"].max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val/1000:.0f}k€",
            va="center", ha="left", fontsize=9,
            color="#1e3a5f", fontweight="bold",
        )

ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
ax2.set_xlim(0, df_top["ca"].max() * 1.18)
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
      AND delivery_days BETWEEN 1 AND 60
"""
df_delai = query(delai_sql)

fig3, ax3 = plt.subplots(figsize=(10, 5))

# Zone livraison rapide
ax3.axvspan(1, 7, alpha=0.12, color="#16A34A", label="Livraison rapide (< 7 jours)")

ax3.hist(df_delai["delivery_days"], bins=range(1, 61), color="#2563EB",
         edgecolor="white", alpha=0.85)
ax3.set_xticks(range(0, 61, 5))

moyenne = df_delai["delivery_days"].mean()
mediane = df_delai["delivery_days"].median()

ax3.axvline(mediane, color="#DC2626", linestyle="--", linewidth=2,
            label=f"Médiane : {mediane:.1f} jours")
ax3.axvline(moyenne, color="#D97706", linestyle="-.", linewidth=2,
            label=f"Moyenne : {moyenne:.1f} jours")

ax3.set_xlabel("Jours")
ax3.set_ylabel("Nombre de commandes")
ax3.legend(fontsize=9)
plt.tight_layout()
st.pyplot(fig3)
plt.close()

st.markdown("---")


# ── Graphique 4 — Boxplot délais par catégorie ────────────────────────────────
st.subheader("📦 Délais de livraison par catégorie")

delai_box_sql = f"""
    SELECT product_category_name_english AS categorie,
           delivery_days
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
      AND delivery_days IS NOT NULL
      AND delivery_days BETWEEN 1 AND 60
"""
df_box = query(delai_box_sql)

# Calcul de la médiane par catégorie pour trier
ordre = (
    df_box.groupby("categorie")["delivery_days"]
    .median()
    .sort_values(ascending=True)
    .index.tolist()
)

data_plot = [df_box[df_box["categorie"] == cat]["delivery_days"].values
             for cat in ordre]

fig4, ax4 = plt.subplots(figsize=(10, max(4, len(ordre) * 0.5)))

bp = ax4.boxplot(
    data_plot,
    vert=False,
    patch_artist=True,
    labels=ordre,
    medianprops=dict(color="#DC2626", linewidth=2),
    boxprops=dict(facecolor="#2563EB", alpha=0.4, color="#2563EB"),
    whiskerprops=dict(color="#2563EB", linewidth=1.5),
    capprops=dict(color="#2563EB", linewidth=1.5),
    flierprops=dict(marker="o", color="#93c5fd", alpha=0.2, markersize=2),
)

# Légende manuelle explicite
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor="#2563EB", alpha=0.4, edgecolor="#2563EB", label="50% des commandes (Q1→Q3)"),
    Line2D([0], [0], color="#DC2626", linewidth=2, label="Médiane"),
    Line2D([0], [0], color="#2563EB", linewidth=1.5, label="Min / Max (hors outliers)"),
    Line2D([0], [0], marker="o", color="#93c5fd", linewidth=0,
           markersize=5, label="Outliers"),
]
ax4.legend(handles=legend_elements, fontsize=9, loc="lower right")

# Limiter l'axe X pour zoomer sur la zone intéressante
ax4.set_xlim(1, 35)
ax4.set_xlabel("Jours")
ax4.text(35.5, -0.5, "→ outliers\n   tronqués", fontsize=7,
         color="gray", va="bottom")

plt.tight_layout()
st.pyplot(fig4)
plt.close()

st.markdown("---")


# ── Graphique 5 — Part des frais de port par catégorie ────────────────────────
st.subheader("🚢 Part des frais de port dans le chiffre d'affaires")

freight_sql = f"""
    SELECT product_category_name_english AS categorie,
           ROUND(AVG(freight_value / revenue) * 100, 1) AS pct_freight,
           COUNT(*) AS nb_commandes
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
      AND revenue > 0
    GROUP BY categorie
    HAVING nb_commandes >= 10
    ORDER BY pct_freight DESC
"""
df_freight = query(freight_sql)

fig5, ax5 = plt.subplots(figsize=(10, max(4, len(df_freight) * 0.45)))
seuil_freight = df_freight["pct_freight"].median()
colors = ["#DC2626" if v > seuil_freight else "#2563EB" for v in df_freight["pct_freight"]]
bars5 = ax5.barh(df_freight["categorie"][::-1], df_freight["pct_freight"][::-1],
                 color=colors[::-1], alpha=0.85)

# Valeurs annotées
for bar, val in zip(bars5, df_freight["pct_freight"][::-1]):
    ax5.text(
        bar.get_width() + 0.3,
        bar.get_y() + bar.get_height() / 2,
        f"{val}%",
        va="center", ha="left", fontsize=9, color="#1e3a5f", fontweight="bold",
    )

# Ligne seuil 20%
ax5.axvline(seuil_freight, color="#D97706", linestyle="--", linewidth=1.5,
            label=f"Médiane : {seuil_freight:.1f}%")
ax5.set_xlim(0, df_freight["pct_freight"].max() * 1.2)
ax5.set_xlabel("Part des frais de port (%)")
ax5.legend(fontsize=9)
plt.tight_layout()
st.pyplot(fig5)
plt.close()

st.markdown("---")


# ── Graphique 6 — Ticket moyen par catégorie ──────────────────────────────────
st.subheader("🎫 Ticket moyen par catégorie")

ticket_sql = f"""
    SELECT product_category_name_english AS categorie,
           ROUND(AVG(price), 2)          AS ticket_moyen,
           COUNT(*)                      AS nb_commandes
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY categorie
    HAVING nb_commandes >= 10
    ORDER BY ticket_moyen DESC
"""
df_ticket = query(ticket_sql)

ticket_moyen_global = df_ticket["ticket_moyen"].mean()

fig6, ax6 = plt.subplots(figsize=(10, max(4, len(df_ticket) * 0.45)))
colors6 = ["#16A34A" if v >= ticket_moyen_global else "#2563EB"
           for v in df_ticket["ticket_moyen"]]
bars6 = ax6.barh(df_ticket["categorie"][::-1], df_ticket["ticket_moyen"][::-1],
                 color=colors6[::-1], alpha=0.85)

# Valeurs annotées
for bar, val in zip(bars6, df_ticket["ticket_moyen"][::-1]):
    ax6.text(
        bar.get_width() + 0.5,
        bar.get_y() + bar.get_height() / 2,
        f"{val:.0f}€",
        va="center", ha="left", fontsize=9, color="#1e3a5f", fontweight="bold",
    )

# Ligne ticket moyen global
ax6.axvline(ticket_moyen_global, color="#D97706", linestyle="--", linewidth=1.5,
            label=f"Moyenne globale : {ticket_moyen_global:.0f}€")
ax6.set_xlim(0, df_ticket["ticket_moyen"].max() * 1.2)
ax6.set_xlabel("Prix moyen (€)")
ax6.legend(fontsize=9)

# Légende couleurs
from matplotlib.patches import Patch
legend_colors = [
    Patch(facecolor="#16A34A", alpha=0.85, label="Au-dessus de la moyenne"),
    Patch(facecolor="#2563EB", alpha=0.85, label="En-dessous de la moyenne"),
]
ax6.legend(handles=legend_colors + [
    plt.Line2D([0], [0], color="#D97706", linestyle="--", linewidth=1.5,
               label=f"Moyenne globale : {ticket_moyen_global:.0f}€")
], fontsize=9)

plt.tight_layout()
st.pyplot(fig6)
plt.close()

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
