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
import plotly.express as px

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


# ── Graphique 1 — CA + volume mensuel ─────────────────────────────────────────
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

fig1 = go.Figure()

# ── Courbe CA ─────────────────────────────────────────────────────────────────
fig1.add_trace(go.Scatter(
    x=df_ca["purchase_month"].tolist(),
    y=df_ca["ca_mensuel"].tolist(),
    mode="lines+markers",
    name="CA mensuel",
    line=dict(color="#2563EB", width=2),
    marker=dict(size=5),
    fill="tozeroy",
    fillcolor="rgba(37,99,235,0.08)",
    yaxis="y1",
    customdata=df_ca[["nb_commandes"]].values.tolist(),
    hovertemplate=(
        "<b>%{x}</b><br>"
        "CA : <b>%{y:,.0f}€</b><br>"
        "Commandes : %{customdata[0]:,.0f}<br>"
        "<extra></extra>"
    ),
))

# ── Courbe volume commandes ───────────────────────────────────────────────────
fig1.add_trace(go.Scatter(
    x=df_ca["purchase_month"].tolist(),
    y=df_ca["nb_commandes"].tolist(),
    mode="lines+markers",
    name="Nb commandes",
    line=dict(color="#16A34A", width=1.5, dash="dash"),
    marker=dict(size=4, symbol="square"),
    yaxis="y2",
    customdata=list(zip(df_ca["ca_mensuel"].tolist())),
    hovertemplate=(
        "<b>%{x}</b><br>"
        "Commandes : <b>%{y:,.0f}</b><br>"
        "CA : %{customdata[0]:,.0f}€<br>"
        "<extra></extra>"
    ),
))

# ── Zone de croissance ────────────────────────────────────────────────────────
if "2017-01" in df_ca["purchase_month"].values and "2017-11" in df_ca["purchase_month"].values:
    fig1.add_vrect(
        x0="2017-01", x1="2017-11",
        fillcolor="#16A34A", opacity=0.07,
        layer="below", line_width=0,
        annotation_text="Période de croissance (jan–nov 2017)",
        annotation_position="top left",
        annotation_font=dict(size=10, color="#16A34A"),
    )

# ── Annotation Black Friday ───────────────────────────────────────────────────
if "2017-11" in df_ca["purchase_month"].values:
    val_bf = df_ca[df_ca["purchase_month"] == "2017-11"]["ca_mensuel"].values[0]
    fig1.add_annotation(
        x="2017-11",
        y=val_bf,
        yref="y1",
        text=f"Pic Black Friday<br>{val_bf/1000:.0f}k€",
        showarrow=True,
        arrowhead=2,
        arrowcolor="#DC2626",
        arrowwidth=1.5,
        ax=-80,
        ay=60,
        font=dict(size=10, color="#DC2626"),
        bgcolor="white",
        bordercolor="#DC2626",
        borderwidth=1.5,
    )

fig1.update_layout(
    height=450,
    margin=dict(l=10, r=10, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(
        title="Mois",
        tickangle=45,
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
    ),
    yaxis=dict(
        title="CA (€)",
        tickformat=",.0f",
        tickfont=dict(size=13, color="#2563EB"),
        title_font=dict(size=13, color="#2563EB"),
        gridcolor="#e5e7eb",
    ),
    yaxis2=dict(
        title="Nombre de commandes",
        overlaying="y",
        side="right",
        tickformat=",",
        tickfont=dict(size=13, color="#16A34A"),
        title_font=dict(size=13, color="#16A34A"),
        showgrid=False,
    ),
)

st.plotly_chart(fig1, use_container_width=True)

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
           ROUND(SUM(revenue), 2)        AS ca,
           COUNT(DISTINCT order_id)      AS nb_commandes,
           ROUND(AVG(price), 2)          AS ticket_moyen
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY categorie
    ORDER BY ca DESC
    LIMIT {n_top}
"""
df_top = query(top_sql)
df_top_sorted = df_top.sort_values("ca", ascending=True)

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=df_top_sorted["ca"].tolist(),
    y=df_top_sorted["categorie"].tolist(),
    orientation="h",
    marker=dict(color="#2563EB", opacity=0.85),
    customdata=df_top_sorted[["nb_commandes", "ticket_moyen"]].values.tolist(),
    hovertemplate=(
        "<b>%{y}</b><br>"
        "CA : <b>%{x:,.0f}€</b><br>"
        "Commandes : %{customdata[0]:,.0f}<br>"
        "Ticket moyen : %{customdata[1]:.2f}€<br>"
        "<extra></extra>"
    ),
    text=[f"{v/1000:.0f}k€" for v in df_top_sorted["ca"]],
    textposition="inside",
    textfont=dict(color="white", size=11),
))

fig2.update_layout(
    xaxis_title="CA (€)",
    yaxis_title="",
    height=max(400, n_top * 45),
    margin=dict(l=10, r=10, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    xaxis=dict(
        gridcolor="#e5e7eb",
        tickformat=",.0f",
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="black"),
    ),
)

st.plotly_chart(fig2, use_container_width=True)

# Insights automatiques
if not df_top.empty:
    meilleur = df_top.iloc[0]
    pire = df_top.iloc[-1]
    col_best, col_worst = st.columns(2)
    with col_best:
        st.success(
            f"✅ **Meilleur CA**\n\n"
            f"**{meilleur['categorie']}** — {meilleur['ca']/1000:.0f}k€"
        )
    with col_worst:
        st.info(
            f"〰️ **CA le plus faible**\n\n"
            f"**{pire['categorie']}** — {pire['ca']/1000:.0f}k€"
        )
st.markdown("---")


# ── Graphique 3 — Distribution des délais de livraison ────────────────────────
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

moyenne = df_delai["delivery_days"].mean()
mediane = df_delai["delivery_days"].median()

fig3 = go.Figure()

# ── Zone livraison rapide ─────────────────────────────────────────────────────
fig3.add_vrect(
    x0=1, x1=7,
    fillcolor="#16A34A", opacity=0.12,
    layer="below", line_width=0,
)

# ── Histogramme ───────────────────────────────────────────────────────────────
fig3.add_trace(go.Histogram(
    x=df_delai["delivery_days"].tolist(),
    xbins=dict(start=1, end=61, size=1),
    marker=dict(color="#2563EB", opacity=0.85, line=dict(color="white", width=0.5)),
    name="Commandes",
    hovertemplate=(
        "Délai : <b>%{x} jours</b><br>"
        "Commandes : <b>%{y:,}</b><br>"
        "<extra></extra>"
    ),
))

# ── Ligne médiane ─────────────────────────────────────────────────────────────
fig3.add_vline(
    x=mediane,
    line_dash="dash",
    line_color="#DC2626",
    line_width=2,
)

# ── Ligne moyenne ─────────────────────────────────────────────────────────────
fig3.add_vline(
    x=moyenne,
    line_dash="dashdot",
    line_color="#D97706",
    line_width=2,
)

# ── Traces invisibles pour la légende ────────────────────────────────────────
fig3.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines",
    name=f"Médiane : {mediane:.1f} jours",
    line=dict(color="#DC2626", width=2, dash="dash"),
))
fig3.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines",
    name=f"Moyenne : {moyenne:.1f} jours",
    line=dict(color="#D97706", width=2, dash="dashdot"),
))
fig3.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines",
    name="Livraison rapide (< 7 jours)",
    line=dict(color="#16A34A", width=8, dash="solid"),
    opacity=0.3,
))

fig3.update_layout(
    xaxis_title="Jours",
    yaxis_title="Nombre de commandes",
    height=450,
    margin=dict(l=10, r=10, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    bargap=0.05,
    showlegend=True,
    legend=dict(
        orientation="v",
        yanchor="top",
        y=0.99,
        xanchor="right",
        x=0.99,
        bgcolor="white",
        bordercolor="#e5e7eb",
        borderwidth=1,
        font=dict(size=11),
    ),
    xaxis=dict(
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
        range=[0, 62],
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
        tickformat=",",
    ),
)

st.plotly_chart(fig3, use_container_width=True)

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

# Tri par médiane croissante
ordre = (
    df_box.groupby("categorie")["delivery_days"]
    .median()
    .sort_values(ascending=True)
    .index.tolist()
)

fig4 = go.Figure()

for cat in ordre:
    data_cat = df_box[df_box["categorie"] == cat]["delivery_days"].tolist()
    fig4.add_trace(go.Box(
        x=data_cat,
        name=cat,
        orientation="h",
        marker=dict(color="#DC2626", opacity=0.3, size=3),
        fillcolor="rgba(37,99,235,0.25)",
        line=dict(color="#2563EB"),
        boxmean=False,
    ))

fig4.update_layout(
    xaxis_title="Jours",
    yaxis_title="",
    height=max(400, len(ordre) * 50),
    margin=dict(l=10, r=10, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    showlegend=False,
    xaxis=dict(
        range=[0, 35],
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="black"),
    ),
)

st.plotly_chart(fig4, use_container_width=True)

# Insights automatiques
if not df_box.empty:
    medianes = df_box.groupby("categorie")["delivery_days"].median()
    meilleur = medianes.idxmin()
    pire = medianes.idxmax()
    val_meilleur = medianes.min()
    val_pire = medianes.max()
    
    col_best, col_worst = st.columns(2)
    with col_best:
        st.success(
            f"✅ **Livraison la plus rapide**\n\n"
            f"**{meilleur}** — médiane {val_meilleur:.0f} jours"
        )
    with col_worst:
        if val_pire > 15:
            label = "⚠️ **Livraison la plus lente**"
            couleur = st.warning
        else:
            label = "〰️ **Livraison la plus lente**"
            couleur = st.info
        couleur(
            f"{label}\n\n"
            f"**{pire}** — médiane {val_pire:.0f} jours"
        )

st.markdown("---")


# ── Graphique 5 — Part des frais de port par catégorie ────────────────────────
st.subheader("🚢 Part des frais de port dans le chiffre d'affaires")

freight_sql = f"""
    SELECT product_category_name_english AS categorie,
           ROUND(AVG(freight_value / revenue) * 100, 1) AS pct_freight,
           COUNT(*) AS nb_commandes,
           ROUND(AVG(price), 2) AS ticket_moyen
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
      AND revenue > 0
    GROUP BY categorie
    HAVING nb_commandes >= 10
    ORDER BY pct_freight DESC
"""
df_freight = query(freight_sql)

seuil_freight = df_freight["pct_freight"].median()
colors_freight = ["#DC2626" if v > seuil_freight else "#2563EB"
                  for v in df_freight["pct_freight"]]

fig5 = go.Figure()

fig5.add_trace(go.Bar(
    x=df_freight["pct_freight"][::-1].tolist(),
    y=df_freight["categorie"][::-1].tolist(),
    orientation="h",
    marker=dict(color=colors_freight[::-1], opacity=0.85),
    customdata=df_freight[["nb_commandes", "ticket_moyen"]][::-1].values.tolist(),
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Frais de port : <b>%{x:.1f}%</b><br>"
        "Commandes : %{customdata[0]:,.0f}<br>"
        "Ticket moyen : %{customdata[1]:.2f}€<br>"
        "<extra></extra>"
    ),
    text=[f"{v:.1f}%" for v in df_freight["pct_freight"][::-1]],
    textposition="outside",
    textfont=dict(size=11, color="#1e3a5f"),
    showlegend=False,
))

# Ligne médiane
fig5.add_vline(
    x=seuil_freight,
    line_dash="dash",
    line_color="#D97706",
    line_width=2,
)

# Traces invisibles pour la légende
fig5.add_trace(go.Bar(x=[None], y=[None], name="Au-dessus de la médiane",
                      marker=dict(color="#DC2626", opacity=0.85)))
fig5.add_trace(go.Bar(x=[None], y=[None], name="En-dessous de la médiane",
                      marker=dict(color="#2563EB", opacity=0.85)))
fig5.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines",
    name=f"Médiane : {seuil_freight:.1f}%",
    line=dict(color="#D97706", width=2, dash="dash"),
))

fig5.update_layout(
    xaxis_title="Part des frais de port (%)",
    yaxis_title="",
    height=max(400, len(df_freight) * 45),
    margin=dict(l=10, r=80, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        bgcolor="white",
        bordercolor="#e5e7eb",
        borderwidth=1,
    ),
    xaxis=dict(
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
        ticksuffix="%",
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="black"),
    ),
    barmode="overlay",
)

st.plotly_chart(fig5, use_container_width=True)

# Insights automatiques
if not df_freight.empty:
    meilleur = df_freight.iloc[-1]
    pire = df_freight.iloc[0]
    col_best, col_worst = st.columns(2)
    with col_best:
        st.success(
            f"✅ **Frais de port les plus faibles**\n\n"
            f"**{meilleur['categorie']}** — {meilleur['pct_freight']:.1f}%"
        )
    with col_worst:
        if pire['pct_freight'] > 25:
            label = "⚠️ **Frais de port les plus élevés**"
            couleur = st.warning
        else:
            label = "〰️ **Frais de port les plus élevés**"
            couleur = st.info
        couleur(
            f"{label}\n\n"
            f"**{pire['categorie']}** — {pire['pct_freight']:.1f}%"
        )

st.markdown("---")


# ── Graphique 6 — Ticket moyen par catégorie ──────────────────────────────────
st.subheader("🎫 Ticket moyen par catégorie")

ticket_sql = f"""
    SELECT product_category_name_english AS categorie,
           ROUND(AVG(price), 2)          AS ticket_moyen,
           COUNT(*)                      AS nb_commandes,
           ROUND(SUM(revenue), 2)        AS ca_total
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY categorie
    HAVING nb_commandes >= 10
    ORDER BY ticket_moyen DESC
"""
df_ticket = query(ticket_sql)

ticket_median_global = df_ticket["ticket_moyen"].median()
colors_ticket = ["#16A34A" if v >= ticket_median_global else "#2563EB"
                 for v in df_ticket["ticket_moyen"]]

fig6 = go.Figure()

fig6.add_trace(go.Bar(
    x=df_ticket["ticket_moyen"][::-1].tolist(),
    y=df_ticket["categorie"][::-1].tolist(),
    orientation="h",
    marker=dict(color=colors_ticket[::-1], opacity=0.85),
    customdata=df_ticket[["nb_commandes", "ca_total"]][::-1].values.tolist(),
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Ticket moyen : <b>%{x:.2f}€</b><br>"
        "Commandes : %{customdata[0]:,.0f}<br>"
        "CA total : %{customdata[1]:,.0f}€<br>"
        "<extra></extra>"
    ),
    text=[f"{v:.0f}€" for v in df_ticket["ticket_moyen"][::-1]],
    textposition="outside",
    textfont=dict(size=11, color="#1e3a5f"),
    showlegend=False,
))

# Ligne médiane
fig6.add_vline(
    x=ticket_median_global,
    line_dash="dash",
    line_color="#D97706",
    line_width=2,
)

# Traces invisibles pour la légende
fig6.add_trace(go.Bar(x=[None], y=[None], name="Au-dessus de la médiane",
                      marker=dict(color="#16A34A", opacity=0.85)))
fig6.add_trace(go.Bar(x=[None], y=[None], name="En-dessous de la médiane",
                      marker=dict(color="#2563EB", opacity=0.85)))
fig6.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines",
    name=f"Médiane : {ticket_median_global:.0f}€",
    line=dict(color="#D97706", width=2, dash="dash"),
))

fig6.update_layout(
    xaxis_title="Prix moyen (€)",
    yaxis_title="",
    height=max(400, len(df_ticket) * 45),
    margin=dict(l=10, r=80, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        bgcolor="white",
        bordercolor="#e5e7eb",
        borderwidth=1,
    ),
    xaxis=dict(
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
        ticksuffix="€",
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="black"),
    ),
    barmode="overlay",
)

st.plotly_chart(fig6, use_container_width=True)

# Insights automatiques
if not df_ticket.empty:
    meilleur = df_ticket.iloc[0]
    pire = df_ticket.iloc[-1]
    col_best, col_worst = st.columns(2)
    with col_best:
        st.success(
            f"✅ **Ticket le plus élevé**\n\n"
            f"**{meilleur['categorie']}** — {meilleur['ticket_moyen']:.0f}€"
        )
    with col_worst:
        st.info(
            f"〰️ **Ticket le plus faible**\n\n"
            f"**{pire['categorie']}** — {pire['ticket_moyen']:.0f}€"
        )

st.markdown("---")

# ── Graphique 7 — Statut des commandes ────────────────────────────────────────
st.subheader("📦 Statut des commandes")

status_sql = f"""
    SELECT 
        CASE 
            WHEN order_status = 'delivered'                          THEN 'Livrées'
            WHEN order_status IN ('shipped', 'processing', 
                                  'invoiced', 'approved')            THEN 'En cours'
            WHEN order_status = 'canceled'                           THEN 'Annulées'
            ELSE 'Indisponibles'
        END AS statut,
        COUNT(*) AS nb
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY statut
    ORDER BY nb DESC
"""
df_status = query(status_sql)
total = df_status["nb"].sum()

colors_status = {
    "Livrées":       "#16A34A",
    "En cours":      "#2563EB",
    "Annulées":      "#DC2626",
    "Indisponibles": "#D97706",
}

# ── Données donut gauche ──────────────────────────────────────────────────────
df_global = df_status.copy()
df_global["groupe"] = df_global["statut"].apply(
    lambda x: "Livrées" if x == "Livrées" else "Autres"
)
df_global = df_global.groupby("groupe")["nb"].sum().reset_index()
df_global = df_global.sort_values("nb", ascending=False)
total_autres = df_global[df_global["groupe"] == "Autres"]["nb"].sum()

# ── Données donut droit ───────────────────────────────────────────────────────
df_autres = df_status[df_status["statut"] != "Livrées"].copy()

fig7 = go.Figure()

# ── Donut gauche ──────────────────────────────────────────────────────────────
fig7.add_trace(go.Pie(
    labels=df_global["groupe"].tolist(),
    values=df_global["nb"].tolist(),
    hole=0.5,
    domain=dict(x=[0, 0.45]),
    marker=dict(colors=["#16A34A", "#DC2626"]),
    textinfo="label+percent",
    textfont=dict(size=13),
    hovertemplate=(
        "<b>%{label}</b><br>"
        "Commandes : <b>%{value:,}</b><br>"
        "Part : %{percent}<br>"
        "<extra></extra>"
    ),
    title=dict(
        text=f"{total:,}<br>commandes".replace(",", " "),
        font=dict(size=13, color="#1e3a5f"),
    ),
    legendgroup="global",
    legendgrouptitle=dict(text="Vue globale", font=dict(size=12, color="#333333")),
))

# ── Donut droit ───────────────────────────────────────────────────────────────
fig7.add_trace(go.Pie(
    labels=df_autres["statut"].tolist(),
    values=df_autres["nb"].tolist(),
    hole=0.5,
    domain=dict(x=[0.55, 1]),
    marker=dict(colors=[colors_status[s] for s in df_autres["statut"]]),
    textinfo="label+percent",
    textfont=dict(size=13),
    hovertemplate=(
        "<b>%{label}</b><br>"
        "Commandes : <b>%{value:,}</b><br>"
        "Part : %{percent}<br>"
        "<extra></extra>"
    ),
    title=dict(
        text=f"{int(total_autres):,}<br>commandes".replace(",", " "),
        font=dict(size=13, color="#1e3a5f"),
    ),
    legendgroup="detail",
    legendgrouptitle=dict(text="Détail non livrées", font=dict(size=12, color="#333333")),
))

fig7.update_layout(
    height=500,
    margin=dict(l=10, r=10, t=60, b=10),
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    annotations=[
        dict(text="Vue globale", x=0.2, y=1.05,
             font=dict(size=13, color="#333333", family="sans-serif"),
             showarrow=False, xref="paper", yref="paper"),
        dict(text="Détail non livrées", x=0.8, y=1.05,
             font=dict(size=13, color="#333333", family="sans-serif"),
             showarrow=False, xref="paper", yref="paper"),
    ],
)

st.plotly_chart(fig7, use_container_width=True)

st.markdown("---")

# ── Graphique 8 — Satisfaction client par catégorie ───────────────────────────
st.subheader("⭐ Satisfaction client par catégorie")

satisfaction_sql = f"""
    SELECT product_category_name_english AS categorie,
           ROUND(AVG(review_score), 2)   AS score_moyen,
           COUNT(*)                      AS nb_avis,
           ROUND(MIN(review_score), 1)   AS score_min,
           ROUND(MAX(review_score), 1)   AS score_max
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
      AND review_score IS NOT NULL
    GROUP BY categorie
    HAVING nb_avis >= 10
    ORDER BY score_moyen DESC
"""
df_satisfaction = query(satisfaction_sql)

score_median = df_satisfaction["score_moyen"].median()
colors_sat = ["#16A34A" if v >= score_median else "#DC2626"
              for v in df_satisfaction["score_moyen"]]

fig8 = go.Figure()

fig8.add_trace(go.Bar(
    x=df_satisfaction["score_moyen"][::-1].tolist(),
    y=df_satisfaction["categorie"][::-1].tolist(),
    orientation="h",
    marker=dict(color=colors_sat[::-1], opacity=0.85),
    customdata=df_satisfaction[["nb_avis", "score_min", "score_max"]][::-1].values.tolist(),
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Score moyen : <b>%{x:.2f}/5</b><br>"
        "Nombre d'avis : %{customdata[0]:,.0f}<br>"
        "Score min : %{customdata[1]:.1f}<br>"
        "Score max : %{customdata[2]:.1f}<br>"
        "<extra></extra>"
    ),
    text=[f"{v:.2f}" for v in df_satisfaction["score_moyen"][::-1]],
    textposition="outside",
    textfont=dict(size=11, color="#1e3a5f"),
    showlegend=False,
))

# Ligne médiane
fig8.add_vline(
    x=score_median,
    line_dash="dash",
    line_color="#D97706",
    line_width=2,
)

# Traces invisibles pour la légende
fig8.add_trace(go.Bar(x=[None], y=[None], name="Au-dessus de la médiane",
                      marker=dict(color="#16A34A", opacity=0.85)))
fig8.add_trace(go.Bar(x=[None], y=[None], name="En-dessous de la médiane",
                      marker=dict(color="#DC2626", opacity=0.85)))
fig8.add_trace(go.Scatter(
    x=[None], y=[None],
    mode="lines",
    name=f"Médiane : {score_median:.2f}",
    line=dict(color="#D97706", width=2, dash="dash"),
))

fig8.update_layout(
    xaxis_title="Score moyen (/5)",
    yaxis_title="",
    height=max(400, len(df_satisfaction) * 45),
    margin=dict(l=10, r=80, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        bgcolor="white",
        bordercolor="#e5e7eb",
        borderwidth=1,
    ),
    xaxis=dict(
        range=[0, 6],
        tickfont=dict(size=13, color="black"),
        title_font=dict(size=13, color="black"),
        gridcolor="#e5e7eb",
    ),
    yaxis=dict(
        tickfont=dict(size=13, color="black"),
    ),
    barmode="overlay",
)

st.plotly_chart(fig8, use_container_width=True)

# Insights automatiques
if not df_satisfaction.empty:
    meilleur = df_satisfaction.iloc[0]
    pire = df_satisfaction.iloc[-1]
    col_best, col_worst = st.columns(2)
    with col_best:
        st.success(
            f"✅ **Meilleure satisfaction**\n\n"
            f"**{meilleur['categorie']}** — {meilleur['score_moyen']:.2f}/5\n\n"
            f"({int(meilleur['nb_avis'])} avis)"
        )
    with col_worst:
        score_pire = pire['score_moyen']
        if score_pire < 3:
            label = "⚠️ **Catégorie à améliorer**"
            couleur = st.error
        elif score_pire < 4:
            label = "〰️ **Catégorie la moins bien notée**"
            couleur = st.warning
        else:
            label = "✅ **Catégorie la moins bien notée**"
            couleur = st.info
        couleur(
            f"{label}\n\n"
            f"**{pire['categorie']}** — {score_pire:.2f}/5\n\n"
            f"({int(pire['nb_avis'])} avis)"
        )

st.markdown("---")

# ── Graphique 9 — Carte choroplèthe par état ──────────────────────────────────
st.subheader("🗺️ Répartition géographique des commandes")

geo_sql = f"""
    SELECT customer_state                    AS state,
           COUNT(DISTINCT order_id)          AS nb_commandes,
           ROUND(SUM(revenue), 2)            AS ca_total,
           ROUND(AVG(review_score), 2)       AS score_moyen
    FROM orders_master
    WHERE purchase_year IN ({years_sql})
      AND product_category_name_english IN ({cats_sql})
    GROUP BY customer_state
    ORDER BY nb_commandes DESC
"""
df_geo = query(geo_sql)

STATES_BR = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}

df_geo["state_name"] = df_geo["state"].map(STATES_BR)

metrique = st.radio(
    "Métrique à afficher sur la carte",
    options=["nb_commandes", "ca_total", "score_moyen"],
    format_func=lambda x: {
        "nb_commandes": "Nombre de commandes",
        "ca_total":     "Chiffre d'affaires (€)",
        "score_moyen":  "Score de satisfaction (/5)",
    }[x],
    horizontal=True,
)

labels_carte = {
    "nb_commandes": "Commandes",
    "ca_total":     "CA (€)",
    "score_moyen":  "Score (/5)",
}

import requests
geojson_url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
geojson_data = requests.get(geojson_url).json()

fig9 = go.Figure(go.Choroplethmapbox(
    geojson=geojson_data,
    locations=df_geo["state"].tolist(),
    featureidkey="properties.sigla",
    z=df_geo[metrique].tolist(),
    colorscale="YlOrRd",
    text=df_geo["state_name"].tolist(),
    customdata=df_geo[["nb_commandes", "ca_total", "score_moyen"]].values.tolist(),
    hovertemplate=(
        "<b>%{text}</b> (%{location})<br>"
        "Commandes : %{customdata[0]:,}<br>"
        "CA : %{customdata[1]:,.0f}€<br>"
        "Score : %{customdata[2]:.2f}/5<br>"
        "<extra></extra>"
    ),
    colorbar=dict(
        title=dict(
            text=labels_carte[metrique],
            font=dict(size=12, color="black"),
        ),
        tickfont=dict(size=11, color="black"),
    ),
    marker_opacity=0.75,
    marker_line_width=0.5,
))

fig9.update_layout(
    mapbox_style="open-street-map",
    mapbox_center={"lat": -14, "lon": -51},
    mapbox_zoom=3,
    height=550,
    margin=dict(l=0, r=0, t=20, b=0),
    paper_bgcolor="white",
    font=dict(family="sans-serif", size=12, color="#333333"),
)

st.plotly_chart(fig9, use_container_width=True)

# Insights
if not df_geo.empty:
    meilleur = df_geo.sort_values(metrique, ascending=False).iloc[0]
    pire = df_geo.sort_values(metrique, ascending=True).iloc[0]

    labels_insight = {
        "nb_commandes": ("✅ **État le plus actif**",     "〰️ **État le moins actif**"),
        "ca_total":     ("✅ **Meilleur CA**",             "〰️ **CA le plus faible**"),
        "score_moyen":  ("✅ **Meilleure satisfaction**",  "〰️ **Satisfaction la plus faible**"),
    }

    valeur_fmt = {
        "nb_commandes": lambda r: f"{int(r['nb_commandes']):,} commandes",
        "ca_total":     lambda r: f"{r['ca_total']/1000:.0f}k€",
        "score_moyen":  lambda r: f"{r['score_moyen']:.2f}/5",
    }

    label_best, label_worst = labels_insight[metrique]

    col_best, col_worst = st.columns(2)
    with col_best:
        st.success(
            f"{label_best}\n\n"
            f"**{STATES_BR.get(meilleur['state'], meilleur['state'])}** ({meilleur['state']}) "
            f"— {valeur_fmt[metrique](meilleur)}"
        )
    with col_worst:
        st.info(
            f"{label_worst}\n\n"
            f"**{STATES_BR.get(pire['state'], pire['state'])}** ({pire['state']}) "
            f"— {valeur_fmt[metrique](pire)}"
        )

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
