"""
analyze.py
----------
Module d'analyse : génération des visualisations KPIs e-commerce.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from src.load import query_sqlite


OUTPUT_PATH = Path("outputs")
sns.set_theme(style="whitegrid")

# Palette cohérente avec le dashboard Streamlit
BLUE    = "#2563EB"
RED     = "#DC2626"
GREEN   = "#16A34A"
AMBER   = "#D97706"


def plot_ca_mensuel() -> None:
    """Chiffre d'affaires mensuel sur toute la période, avec annotations."""
    sql = """
        SELECT purchase_month,
               ROUND(SUM(revenue), 2) AS ca_mensuel
        FROM orders_master
        GROUP BY purchase_month
        ORDER BY purchase_month
    """
    df = query_sqlite(sql)

    fig, ax = plt.subplots(figsize=(14, 5))

    # Courbe principale
    ax.plot(df["purchase_month"], df["ca_mensuel"],
            marker="o", color=BLUE, linewidth=2, zorder=3)
    ax.fill_between(range(len(df)), df["ca_mensuel"],
                    alpha=0.1, color=BLUE)

    # ── Zone de croissance (2017-01 → 2017-11) ────────────────────────────
    idx_debut  = df[df["purchase_month"] == "2017-01"].index
    idx_pic    = df[df["purchase_month"] == "2017-11"].index

    if len(idx_debut) and len(idx_pic):
        i_debut = df.index.get_loc(idx_debut[0])
        i_pic   = df.index.get_loc(idx_pic[0])
        ax.axvspan(i_debut, i_pic, alpha=0.07, color=GREEN,
                   label="Période de croissance (jan–nov 2017)")

    # ── Annotation pic novembre 2017 (Black Friday) ───────────────────────
    idx_bf = df[df["purchase_month"] == "2017-11"].index
    if len(idx_bf):
        i_bf   = df.index.get_loc(idx_bf[0])
        val_bf = df.loc[idx_bf[0], "ca_mensuel"]
        ax.annotate(
            f"Pic Black Friday\n{val_bf/1000:.0f}k€",
            xy=(i_bf, val_bf),
            xytext=(i_bf - 4, val_bf * 0.75),
            fontsize=9,
            color=RED,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=RED, alpha=0.85),
        )

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["purchase_month"], rotation=45, ha="right", fontsize=8)
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€")
    )
    ax.set_title("Chiffre d'affaires mensuel", fontsize=14, fontweight="bold")
    ax.set_xlabel("Mois")
    ax.set_ylabel("CA (k€)")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "ca_mensuel.png", dpi=150)
    plt.close()
    print("✅ ca_mensuel.png sauvegardé")


def plot_top_categories() -> None:
    """Top 10 catégories par CA, avec valeurs annotées sur chaque barre."""
    sql = """
        SELECT product_category_name_english AS categorie,
               ROUND(SUM(revenue), 2) AS ca
        FROM orders_master
        WHERE product_category_name_english IS NOT NULL
        GROUP BY categorie
        ORDER BY ca DESC
        LIMIT 10
    """
    df = query_sqlite(sql)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df["categorie"][::-1], df["ca"][::-1], color=BLUE, alpha=0.85)

    # ── Valeur annotée : intérieur si barre assez grande, extérieur sinon ─
    seuil = df["ca"].max() * 0.15  # barre trop courte si < 15% du max
    for bar, val in zip(bars, df["ca"][::-1]):
        if bar.get_width() >= seuil:
            # Texte blanc à l'intérieur
            ax.text(
                bar.get_width() - df["ca"].max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val/1000:.0f}k€",
                va="center", ha="right", fontsize=9,
                color="white", fontweight="bold",
            )
        else:
            # Texte bleu foncé à l'extérieur
            ax.text(
                bar.get_width() + df["ca"].max() * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val/1000:.0f}k€",
                va="center", ha="left", fontsize=9,
                color="#1e3a5f", fontweight="bold",
            )

    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€")
    )
    ax.set_xlim(0, df["ca"].max() * 1.18)
    ax.set_title("Top 10 catégories par chiffre d'affaires",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("CA (k€)")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "top_categories.png", dpi=150)
    plt.close()
    print("✅ top_categories.png sauvegardé")


def plot_delai_livraison() -> None:
    """
    Distribution des délais de livraison.
    Annotations : moyenne, médiane, zone livraison rapide (< 7 jours).
    """
    sql = """
        SELECT delivery_days
        FROM orders_master
        WHERE delivery_days IS NOT NULL
          AND delivery_days BETWEEN 0 AND 60
    """
    df = query_sqlite(sql)

    moyenne = df["delivery_days"].mean()
    mediane = df["delivery_days"].median()

    fig, ax = plt.subplots(figsize=(10, 5))

    # ── Zone livraison rapide ──────────────────────────────────────────────
    ax.axvspan(0, 7, alpha=0.12, color=GREEN, label="Livraison rapide (< 7 jours)")

    ax.hist(df["delivery_days"], bins=40, color=BLUE,
            edgecolor="white", alpha=0.85)

    # ── Moyenne ───────────────────────────────────────────────────────────
    ax.axvline(moyenne, color=RED, linestyle="--", linewidth=2,
               label=f"Moyenne : {moyenne:.1f} jours")

    # ── Médiane ───────────────────────────────────────────────────────────
    ax.axvline(mediane, color=AMBER, linestyle="-.", linewidth=2,
               label=f"Médiane : {mediane:.1f} jours")

    ax.set_title("Distribution des délais de livraison",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Jours")
    ax.set_ylabel("Nombre de commandes")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "delai_livraison.png", dpi=150)
    plt.close()
    print("✅ delai_livraison.png sauvegardé")

def plot_freight_ratio() -> None:
    """Part des frais de port dans le CA par catégorie."""
    sql = """
        SELECT product_category_name_english AS categorie,
               ROUND(AVG(freight_value / revenue) * 100, 1) AS pct_freight,
               COUNT(*) AS nb_commandes
        FROM orders_master
        WHERE revenue > 0
          AND product_category_name_english IS NOT NULL
        GROUP BY categorie
        HAVING nb_commandes >= 10
        ORDER BY pct_freight DESC
    """
    df = query_sqlite(sql)

    seuil = df["pct_freight"].median()
    colors = ["#DC2626" if v > seuil else "#2563EB" for v in df["pct_freight"]]

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.45)))
    bars = ax.barh(df["categorie"][::-1], df["pct_freight"][::-1],
                   color=colors[::-1], alpha=0.85)

    for bar, val in zip(bars, df["pct_freight"][::-1]):
        ax.text(
            bar.get_width() + 0.3,
            bar.get_y() + bar.get_height() / 2,
            f"{val}%",
            va="center", ha="left", fontsize=9,
            color="#1e3a5f", fontweight="bold",
        )

    ax.axvline(seuil, color="#D97706", linestyle="--", linewidth=1.5,
               label=f"Médiane : {seuil:.1f}%")
    ax.set_xlim(0, df["pct_freight"].max() * 1.2)
    ax.set_title("Part des frais de port dans le chiffre d'affaires",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Part des frais de port (%)")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "freight_ratio.png", dpi=150)
    plt.close()
    print("✅ freight_ratio.png sauvegardé")


def plot_ticket_moyen() -> None:
    """Ticket moyen par catégorie avec ligne de référence médiane."""
    sql = """
        SELECT product_category_name_english AS categorie,
               ROUND(AVG(price), 2)          AS ticket_moyen,
               COUNT(*)                      AS nb_commandes
        FROM orders_master
        WHERE product_category_name_english IS NOT NULL
        GROUP BY categorie
        HAVING nb_commandes >= 10
        ORDER BY ticket_moyen DESC
    """
    df = query_sqlite(sql)

    ticket_median_global = df["ticket_moyen"].median()
    colors = ["#16A34A" if v >= ticket_median_global else "#2563EB"
              for v in df["ticket_moyen"]]

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.45)))
    bars = ax.barh(df["categorie"][::-1], df["ticket_moyen"][::-1],
                   color=colors[::-1], alpha=0.85)

    for bar, val in zip(bars, df["ticket_moyen"][::-1]):
        ax.text(
            bar.get_width() + 0.5,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.0f}€",
            va="center", ha="left", fontsize=9,
            color="#1e3a5f", fontweight="bold",
        )

    ax.axvline(ticket_median_global, color="#D97706", linestyle="--", linewidth=1.5,
               label=f"Médiane globale : {ticket_median_global:.0f}€")
    ax.set_xlim(0, df["ticket_moyen"].max() * 1.2)
    ax.set_title("Ticket moyen par catégorie", fontsize=14, fontweight="bold")
    ax.set_xlabel("Prix moyen (€)")

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#16A34A", alpha=0.85, label="Au-dessus de la médiane"),
        Patch(facecolor="#2563EB", alpha=0.85, label="En-dessous de la médiane"),
        plt.Line2D([0], [0], color="#D97706", linestyle="--", linewidth=1.5,
                   label=f"Médiane globale : {ticket_median_global:.0f}€"),
    ]
    ax.legend(handles=legend_elements, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "ticket_moyen.png", dpi=150)
    plt.close()
    print("✅ ticket_moyen.png sauvegardé")


def plot_boxplot_delais() -> None:
    """Boxplot des délais de livraison par catégorie."""
    sql = """
        SELECT product_category_name_english AS categorie,
               delivery_days
        FROM orders_master
        WHERE delivery_days IS NOT NULL
          AND delivery_days BETWEEN 1 AND 60
          AND product_category_name_english IS NOT NULL
    """
    df = query_sqlite(sql)

    ordre = (
        df.groupby("categorie")["delivery_days"]
        .median()
        .sort_values(ascending=True)
        .index.tolist()
    )
    data_plot = [df[df["categorie"] == cat]["delivery_days"].values
                 for cat in ordre]

    fig, ax = plt.subplots(figsize=(10, max(4, len(ordre) * 0.5)))
    ax.boxplot(
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

    ax.set_xlim(1, 35)
    ax.set_title("Délais de livraison par catégorie", fontsize=14, fontweight="bold")
    ax.set_xlabel("Jours")

    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2563EB", alpha=0.4, edgecolor="#2563EB",
              label="50% des commandes (Q1→Q3)"),
        Line2D([0], [0], color="#DC2626", linewidth=2, label="Médiane"),
        Line2D([0], [0], color="#2563EB", linewidth=1.5, label="Min / Max (hors outliers)"),
        Line2D([0], [0], marker="o", color="#93c5fd", linewidth=0,
               markersize=5, label="Outliers"),
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc="lower right")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "boxplot_delais.png", dpi=150)
    plt.close()
    print("✅ boxplot_delais.png sauvegardé")

def run_analysis() -> None:
    """Lance toutes les visualisations."""
    print("Génération des visualisations...")
    plot_ca_mensuel()
    plot_top_categories()
    plot_delai_livraison()
    plot_freight_ratio()
    plot_ticket_moyen()
    plot_boxplot_delais()
    print("✅ Toutes les visualisations sont dans outputs/")