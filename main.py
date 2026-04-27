"""
main.py
-------
Point d'entrée du pipeline ETL.
"""
from src.extract import load_all_datasets
from src.transform import run_transformations
from src.load import save_to_sqlite, query_sqlite
from src.analyze import run_analysis
from src.validate import validate_raw_data, validate_master_table

if __name__ == "__main__":
    print("=== EXTRACTION ===")
    datasets = load_all_datasets()
    validate_raw_data(datasets)

    print("\n=== TRANSFORMATION ===")
    df = run_transformations(datasets)
    validate_master_table(df)

    print("\n=== CHARGEMENT SQL ===")
    save_to_sqlite(df)

    print("\n=== TEST REQUÊTE SQL ===")
    sql = """
        SELECT purchase_year,
               COUNT(DISTINCT order_id) AS nb_commandes,
               ROUND(SUM(revenue), 2)   AS chiffre_affaires
        FROM orders_master
        GROUP BY purchase_year
        ORDER BY purchase_year
    """
    result = query_sqlite(sql)
    print(result)

    print("\n=== ANALYSE & VISUALISATION ===")
    run_analysis()