"""
analyze.py
----------
Module d'analyse : génération des visualisations KPIs e-commerce.
"""

import logging
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from src.load import query_sqlite


# ── Configuration ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

OUTPUT_PATH = Path("outputs")
sns.set_theme(style="whitegrid")

BLUE  = "#2563EB"
RED   = "#DC2626"
GREEN = "#16A34A"
AMBER = "#D97706"

TOP10_CAT = """
    SELECT product_category_name_english
    FROM orders_master
    WHERE product_category_name_english IS NOT NULL
    GROUP BY product_category_name_english
    ORDER BY SUM(revenue) DESC
    LIMIT 10
"""


def plot_ca_mensuel() -> None:
    """Chiffre d'affaires mensuel sur toute la periode, avec annotations."""
    sql = """
        SELECT purchase_month,
            ROUND(SUM(revenue), 2)   AS ca_mensuel,
            COUNT(DISTINCT order_id) AS nb_commandes
        FROM orders_master
        WHERE product_category_name_english IN ({TOP10_CAT})
        GROUP BY purchase_month
        ORDER BY purchase_month
    """.format(TOP10_CAT=TOP10_CAT)
    df = query_sqlite(sql)

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(df["purchase_month"], df["ca_mensuel"],
            marker="o", color=BLUE, linewidth=2, zorder=3)
    ax.fill_between(range(len(df)), df["ca_mensuel"], alpha=0.1, color=BLUE)

    ax2 = ax.twinx()
    ax2.plot(range(len(df)), df["nb_commandes"],
             marker="s", color=GREEN, linewidth=1.5,
             linestyle="--", label="Nb commandes", zorder=2)
    ax2.set_ylabel("Nombre de commandes", color=GREEN)
    ax2.tick_params(axis="y", labelcolor=GREEN)

    idx_debut = df[df["purchase_month"] == "2017-01"].index
    idx_pic   = df[df["purchase_month"] == "2017-11"].index
    if len(idx_debut) and len(idx_pic):
        i_debut = df.index.get_loc(idx_debut[0])
        i_pic   = df.index.get_loc(idx_pic[0])
        ax.axvspan(i_debut, i_pic, alpha=0.07, color=GREEN,
                   label="Periode de croissance (jan-nov 2017)")

    idx_bf = df[df["purchase_month"] == "2017-11"].index
    if len(idx_bf):
        i_bf   = df.index.get_loc(idx_bf[0])
        val_bf = df.loc[idx_bf[0], "ca_mensuel"]
        ax.annotate(
            f"Pic Black Friday\n{val_bf/1000:.0f}k€",
            xy=(i_bf, val_bf),
            xytext=(i_bf - 4, val_bf * 0.75),
            fontsize=9, color=RED,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.5),
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=RED, alpha=0.85),
        )

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=9, loc="upper left")

    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["purchase_month"], rotation=45, ha="right", fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
    ax.set_title("Chiffre d'affaires mensuel + volume de commandes",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Mois")
    ax.set_ylabel("CA (k€)")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "ca_mensuel.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : ca_mensuel.png")


def plot_top_categories() -> None:
    """Top 10 categories par CA, avec valeurs annotees sur chaque barre."""
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

    seuil = df["ca"].max() * 0.15
    for bar, val in zip(bars, df["ca"][::-1]):
        if bar.get_width() >= seuil:
            ax.text(bar.get_width() - df["ca"].max() * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val/1000:.0f}k€",
                    va="center", ha="right", fontsize=9,
                    color="white", fontweight="bold")
        else:
            ax.text(bar.get_width() + df["ca"].max() * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val/1000:.0f}k€",
                    va="center", ha="left", fontsize=9,
                    color="#1e3a5f", fontweight="bold")

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
    ax.set_xlim(0, df["ca"].max() * 1.18)
    ax.set_title("Top 10 categories par chiffre d'affaires",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("CA (k€)")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "top_categories.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : top_categories.png")


def plot_delai_livraison() -> None:
    """Distribution des delais de livraison avec annotations."""
    sql = """
        SELECT delivery_days
        FROM orders_master
        WHERE delivery_days IS NOT NULL
        AND delivery_days BETWEEN 1 AND 60
        AND product_category_name_english IN ({TOP10_CAT})
    """.format(TOP10_CAT=TOP10_CAT)
    df = query_sqlite(sql)

    moyenne = df["delivery_days"].mean()
    mediane = df["delivery_days"].median()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.axvspan(0, 7, alpha=0.12, color=GREEN, label="Livraison rapide (< 7 jours)")
    ax.hist(df["delivery_days"], bins=40, color=BLUE, edgecolor="white", alpha=0.85)
    ax.axvline(moyenne, color=RED, linestyle="--", linewidth=2,
               label=f"Moyenne : {moyenne:.1f} jours")
    ax.axvline(mediane, color=AMBER, linestyle="-.", linewidth=2,
               label=f"Mediane : {mediane:.1f} jours")
    ax.set_title("Distribution des delais de livraison",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Jours")
    ax.set_ylabel("Nombre de commandes")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "delai_livraison.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : delai_livraison.png")


def plot_freight_ratio() -> None:
    """Part des frais de port dans le CA par categorie."""
    sql = """
        SELECT product_category_name_english AS categorie,
            ROUND(AVG(freight_value / revenue) * 100, 1) AS pct_freight
        FROM orders_master
        WHERE revenue > 0
        AND product_category_name_english IN ({TOP10_CAT})
        GROUP BY categorie
        ORDER BY pct_freight DESC
    """.format(TOP10_CAT=TOP10_CAT)
    df = query_sqlite(sql)

    seuil  = df["pct_freight"].median()
    colors = [RED if v > seuil else BLUE for v in df["pct_freight"]]

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.45)))
    bars = ax.barh(df["categorie"][::-1], df["pct_freight"][::-1],
                   color=colors[::-1], alpha=0.85)

    for bar, val in zip(bars, df["pct_freight"][::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{val}%", va="center", ha="left", fontsize=9,
                color="#1e3a5f", fontweight="bold")

    ax.axvline(seuil, color=AMBER, linestyle="--", linewidth=1.5,
               label=f"Mediane : {seuil:.1f}%")
    ax.set_xlim(0, df["pct_freight"].max() * 1.2)
    ax.set_title("Part des frais de port dans le chiffre d'affaires",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Part des frais de port (%)")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "freight_ratio.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : freight_ratio.png")


def plot_ticket_moyen() -> None:
    """Ticket moyen par categorie avec ligne de reference mediane."""
    sql = """
        SELECT product_category_name_english AS categorie,
            ROUND(AVG(price), 2) AS ticket_moyen
        FROM orders_master
        WHERE product_category_name_english IN ({TOP10_CAT})
        GROUP BY categorie
        ORDER BY ticket_moyen DESC
    """.format(TOP10_CAT=TOP10_CAT)
    df = query_sqlite(sql)

    ticket_median_global = df["ticket_moyen"].median()
    colors = [GREEN if v >= ticket_median_global else BLUE for v in df["ticket_moyen"]]

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.45)))
    bars = ax.barh(df["categorie"][::-1], df["ticket_moyen"][::-1],
                   color=colors[::-1], alpha=0.85)

    for bar, val in zip(bars, df["ticket_moyen"][::-1]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}€", va="center", ha="left", fontsize=9,
                color="#1e3a5f", fontweight="bold")

    ax.axvline(ticket_median_global, color=AMBER, linestyle="--", linewidth=1.5,
               label=f"Mediane globale : {ticket_median_global:.0f}€")
    ax.set_xlim(0, df["ticket_moyen"].max() * 1.2)
    ax.set_title("Ticket moyen par categorie", fontsize=14, fontweight="bold")
    ax.set_xlabel("Prix moyen (€)")

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=GREEN, alpha=0.85, label="Au-dessus de la mediane"),
        Patch(facecolor=BLUE,  alpha=0.85, label="En-dessous de la mediane"),
        plt.Line2D([0], [0], color=AMBER, linestyle="--", linewidth=1.5,
                   label=f"Mediane globale : {ticket_median_global:.0f}€"),
    ]
    ax.legend(handles=legend_elements, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "ticket_moyen.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : ticket_moyen.png")


def plot_boxplot_delais() -> None:
    """Boxplot des delais de livraison par categorie (Top 10 CA)."""
    sql = """
        SELECT product_category_name_english AS categorie,
            delivery_days
        FROM orders_master
        WHERE delivery_days IS NOT NULL
        AND delivery_days BETWEEN 1 AND 60
        AND product_category_name_english IN ({TOP10_CAT})
    """.format(TOP10_CAT=TOP10_CAT)
    df = query_sqlite(sql)

    ordre = (
        df.groupby("categorie")["delivery_days"]
        .median()
        .sort_values(ascending=True)
        .index.tolist()
    )
    data_plot = [df[df["categorie"] == cat]["delivery_days"].values for cat in ordre]

    fig, ax = plt.subplots(figsize=(10, max(4, len(ordre) * 0.5)))
    ax.boxplot(
        data_plot, vert=False, patch_artist=True, labels=ordre,
        medianprops=dict(color=RED, linewidth=2),
        boxprops=dict(facecolor=BLUE, alpha=0.4, color=BLUE),
        whiskerprops=dict(color=BLUE, linewidth=1.5),
        capprops=dict(color=BLUE, linewidth=1.5),
        flierprops=dict(marker="o", color="#93c5fd", alpha=0.2, markersize=2),
    )
    ax.set_xlim(1, 35)
    ax.set_title("Delais de livraison par categorie", fontsize=14, fontweight="bold")
    ax.set_xlabel("Jours")

    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=BLUE, alpha=0.4, edgecolor=BLUE, label="50% des commandes (Q1-Q3)"),
        Line2D([0], [0], color=RED, linewidth=2, label="Mediane"),
        Line2D([0], [0], color=BLUE, linewidth=1.5, label="Min / Max (hors outliers)"),
        Line2D([0], [0], marker="o", color="#93c5fd", linewidth=0,
               markersize=5, label="Outliers"),
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc="lower right")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "boxplot_delais.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : boxplot_delais.png")


def plot_statut_commandes() -> None:
    """Double donut : vue globale + detail des commandes non livrees."""
    sql = """
        SELECT
            CASE
                WHEN order_status = 'delivered'                       THEN 'Livrees'
                WHEN order_status IN ('shipped', 'processing',
                                      'invoiced', 'approved')         THEN 'En cours'
                WHEN order_status = 'canceled'                        THEN 'Annulees'
                ELSE 'Indisponibles'
            END AS statut,
            COUNT(*) AS nb
        FROM orders_master
        GROUP BY statut
        ORDER BY nb DESC
    """
    df = query_sqlite(sql)
    total = df["nb"].sum()

    fig, (ax_global, ax_detail) = plt.subplots(1, 2, figsize=(14, 7))

    df_global = df.copy()
    df_global["groupe"] = df_global["statut"].apply(
        lambda x: "Livrees" if x == "Livrees" else "Autres"
    )
    df_global = df_global.groupby("groupe")["nb"].sum().reset_index()
    df_global = df_global.sort_values("nb", ascending=False)

    colors_global = {"Livrees": GREEN, "Autres": RED}
    colors_left   = [colors_global[s] for s in df_global["groupe"]]

    wedges1, texts1, autotexts1 = ax_global.pie(
        df_global["nb"], labels=df_global["groupe"], autopct="%1.1f%%",
        colors=colors_left, pctdistance=0.75,
        wedgeprops=dict(width=0.5), startangle=90,
    )
    for text in texts1:
        text.set_fontsize(12)
    for autotext in autotexts1:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")
        autotext.set_color("white")

    ax_global.text(0, 0, f"{total:,}\ncommandes".replace(",", " "),
                   ha="center", va="center", fontsize=12,
                   fontweight="bold", color="#1e3a5f")
    ax_global.set_title("Vue globale", fontsize=13, fontweight="bold", pad=20)

    df_autres     = df[df["statut"] != "Livrees"].copy()
    total_autres  = df_autres["nb"].sum()
    colors_detail = {"En cours": BLUE, "Annulees": RED, "Indisponibles": AMBER}
    colors_right  = [colors_detail.get(s, "#6B7280") for s in df_autres["statut"]]

    wedges2, texts2, autotexts2 = ax_detail.pie(
        df_autres["nb"], labels=df_autres["statut"], autopct="%1.1f%%",
        colors=colors_right, pctdistance=0.75,
        wedgeprops=dict(width=0.5), startangle=90,
    )
    for text in texts2:
        text.set_fontsize(12)
    for autotext in autotexts2:
        autotext.set_fontsize(11)
        autotext.set_fontweight("bold")
        autotext.set_color("white")

    ax_detail.text(0, 0, f"{total_autres:,}\ncommandes".replace(",", " "),
                   ha="center", va="center", fontsize=12,
                   fontweight="bold", color="#1e3a5f")
    ax_detail.set_title("Detail des commandes non livrees",
                        fontsize=13, fontweight="bold", pad=20)

    plt.suptitle("Repartition des statuts de commandes",
                 fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "statut_commandes.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : statut_commandes.png")


def plot_satisfaction_categories() -> None:
    """Score de satisfaction moyen par categorie (Top 10 CA)."""
    sql = """
        SELECT product_category_name_english AS categorie,
               ROUND(AVG(review_score), 2)   AS score_moyen,
               COUNT(*)                      AS nb_avis
        FROM orders_master
        WHERE review_score IS NOT NULL
          AND product_category_name_english IN ({TOP10_CAT})
        GROUP BY categorie
        HAVING nb_avis >= 10
        ORDER BY score_moyen DESC
    """.format(TOP10_CAT=TOP10_CAT)
    df = query_sqlite(sql)

    score_median = df["score_moyen"].median()
    colors = [GREEN if v >= score_median else RED for v in df["score_moyen"]]

    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.45)))
    bars = ax.barh(df["categorie"][::-1], df["score_moyen"][::-1],
                   color=colors[::-1], alpha=0.85)

    for bar, val in zip(bars, df["score_moyen"][::-1]):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}", va="center", ha="left", fontsize=9,
                color="#1e3a5f", fontweight="bold")

    ax.axvline(score_median, color=AMBER, linestyle="--", linewidth=1.5,
               label=f"Mediane : {score_median:.2f}")
    ax.set_xlim(0, 6)
    ax.set_xlabel("Score moyen (/5)")
    ax.set_title("Satisfaction client par categorie",
                 fontsize=14, fontweight="bold")

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=GREEN, alpha=0.85, label="Au-dessus de la mediane"),
        Patch(facecolor=RED,   alpha=0.85, label="En-dessous de la mediane"),
        plt.Line2D([0], [0], color=AMBER, linestyle="--", linewidth=1.5,
                   label=f"Mediane : {score_median:.2f}"),
    ]
    ax.legend(handles=legend_elements, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "satisfaction_categories.png", dpi=150)
    plt.close()
    logger.info("Visualisation sauvegardee : satisfaction_categories.png")


def run_analysis() -> None:
    """Lance toutes les visualisations et les sauvegarde dans outputs/."""
    logger.info("Generation des visualisations...")
    plot_ca_mensuel()
    plot_top_categories()
    plot_delai_livraison()
    plot_freight_ratio()
    plot_ticket_moyen()
    plot_boxplot_delais()
    plot_statut_commandes()
    plot_satisfaction_categories()
    logger.info("Toutes les visualisations sont dans '%s'", OUTPUT_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_analysis()