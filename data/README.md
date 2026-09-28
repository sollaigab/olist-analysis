# Data

## Provenance

- **Dataset**: Brazilian E-Commerce Public Dataset by Olist
- **Publisher**: Olist (Brazilian marketplace), released on Kaggle
- **Kaggle slug**: `olistbr/brazilian-ecommerce`
- **Coverage**: ~100k orders placed between 2016 and 2018 across Brazilian
  marketplaces, with the order, item, payment, review, customer, seller,
  product and geolocation tables that describe them.
- **Anonymisation**: performed by the publisher. Company and partner names were
  replaced with fictional references; customer and seller identifiers are
  surrogate keys.

## Licence

Published under **CC BY-NC-SA 4.0** (Attribution, NonCommercial, ShareAlike).
This repository uses the data for a non-commercial portfolio analysis and
redistributes **no raw records** — only derived aggregates under
`dashboard/exports/`, which remain subject to the same licence terms.

## What is versioned and what is not

| Path | Versioned | Why |
|---|---|---|
| `data/raw/` | No | Source CSVs. Re-downloadable, large, licence-bound. |
| `data/processed/` | No | Fully derived from `raw/` by the pipeline. |
| `data/olist.duckdb` | No | Local database, rebuilt by `src/ingest.py`. |
| `dashboard/exports/*.csv` | Yes | Small aggregates, needed to open the dashboard. |
| This file | Yes | Provenance must travel with the repo. |

## How to obtain the files

Either configure a Kaggle API token and run `python src/ingest.py --download`,
or download the archive manually from the Kaggle dataset page and unzip the
nine CSV files directly into `data/raw/`.

Expected files:

```
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

`src/ingest.py` verifies all nine are present and aborts with the list of
missing files rather than building a partial database.

## Integrity

After the first successful ingest, record row counts per table in
`sql/10_quality/` so that any later re-download can be checked against the
figures the analysis was actually built on.
