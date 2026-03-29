"""
analyze.py
----------
Module d'analyse : génération des visualisations KPIs e-commerce.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path
from src.load import query_sqlite


OUTPUT_PATH = Path("outputs")
sns.set_theme(style="whitegrid")


def plot_ca_mensuel() -> None:
    """Chiffre d'affaires mensuel sur toute la période."""
    sql = """
        SELECT purchase_month,
               ROUND(SUM(revenue), 2) AS ca_mensuel
        FROM orders_master
        GROUP BY purchase_month
        ORDER BY purchase_month
    """
    df = query_sqlite(sql)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(df["purchase_month"], df["ca_mensuel"], marker="o", color="#2563EB", linewidth=2)
    ax.fill_between(range(len(df)), df["ca_mensuel"], alpha=0.1, color="#2563EB")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["purchase_month"], rotation=45, ha="right", fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
    ax.set_title("Chiffre d'affaires mensuel", fontsize=14, fontweight="bold")
    ax.set_xlabel("Mois")
    ax.set_ylabel("CA (k€)")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "ca_mensuel.png", dpi=150)
    plt.close()
    print("✅ ca_mensuel.png sauvegardé")


def plot_top_categories() -> None:
    """Top 10 catégories de produits par chiffre d'affaires."""
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
    bars = ax.barh(df["categorie"][::-1], df["ca"][::-1], color="#2563EB")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}k€"))
    ax.set_title("Top 10 catégories par chiffre d'affaires", fontsize=14, fontweight="bold")
    ax.set_xlabel("CA (k€)")
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "top_categories.png", dpi=150)
    plt.close()
    print("✅ top_categories.png sauvegardé")


def plot_delai_livraison() -> None:
    """Distribution des délais de livraison."""
    sql = """
        SELECT delivery_days
        FROM orders_master
        WHERE delivery_days IS NOT NULL
          AND delivery_days BETWEEN 0 AND 60
    """
    df = query_sqlite(sql)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(df["delivery_days"], bins=40, color="#2563EB", edgecolor="white", alpha=0.85)
    ax.axvline(df["delivery_days"].mean(), color="#DC2626", linestyle="--",
               linewidth=2, label=f"Moyenne : {df['delivery_days'].mean():.1f} jours")
    ax.set_title("Distribution des délais de livraison", fontsize=14, fontweight="bold")
    ax.set_xlabel("Jours")
    ax.set_ylabel("Nombre de commandes")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH / "delai_livraison.png", dpi=150)
    plt.close()
    print("✅ delai_livraison.png sauvegardé")


def run_analysis() -> None:
    """Lance toutes les visualisations."""
    print("Génération des visualisations...")
    plot_ca_mensuel()
    plot_top_categories()
    plot_delai_livraison()
    print("✅ Toutes les visualisations sont dans outputs/")