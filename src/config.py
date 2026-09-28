"""Central paths and dataset manifest.

Every other module imports paths from here so that nothing hardcodes a
location. Keeps the repo portable across machines.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "olist.duckdb"

SQL_DIR = PROJECT_ROOT / "sql"
EXPORT_DIR = PROJECT_ROOT / "dashboard" / "exports"
FIGURE_DIR = PROJECT_ROOT / "reports" / "figures"

KAGGLE_DATASET = "olistbr/brazilian-ecommerce"

# Source file -> raw table name.
# Filenames come from the Kaggle distribution; ingest fails loudly if one is
# missing rather than silently producing a partial database.
SOURCE_FILES: dict[str, str] = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "category_translation",
}

SCHEMAS = ["raw", "stg", "int", "mart"]
