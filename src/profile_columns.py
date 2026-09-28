"""Generate reports/data_dictionary.md from the database, not from memory.

Every number in the dictionary is produced by a query executed at generation
time, so the document cannot drift away from the data it describes. Re-run it
after any change to the staging layer.

Usage:
    python src/profile_columns.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH, PROJECT_ROOT  # noqa: E402

OUT_PATH = PROJECT_ROOT / "reports" / "data_dictionary.md"

# Declared grain and keys per staging table. These are assertions about the
# model; tests/test_grain.py verifies each one against the data.
GRAIN: dict[str, tuple[str, str]] = {
    "orders":              ("1 row = 1 order",                      "order_id"),
    "order_items":         ("1 row = 1 item line within an order",  "(order_id, order_item_id)"),
    "order_payments":      ("1 row = 1 payment instrument on an order", "(order_id, payment_sequential)"),
    "order_reviews":       ("1 row = 1 review of 1 order",          "(review_id, order_id)"),
    "customers":           ("1 row = 1 per-order customer record",  "customer_id"),
    "sellers":             ("1 row = 1 seller",                     "seller_id"),
    "products":            ("1 row = 1 product",                    "product_id"),
    "category_translation": ("1 row = 1 category name",             "category_pt"),
    "geolocation":         ("1 row = 1 zip prefix (deduplicated)",  "zip_prefix"),
}

MAX_SAMPLE_CHARS = 26


def sample_values(con, table: str, column: str, n: int = 3) -> str:
    rows = con.execute(
        f'SELECT DISTINCT "{column}" FROM stg.{table} '
        f'WHERE "{column}" IS NOT NULL ORDER BY 1 LIMIT {n}'
    ).fetchall()
    out = []
    for (value,) in rows:
        text = str(value)
        out.append(text[:MAX_SAMPLE_CHARS] + "…" if len(text) > MAX_SAMPLE_CHARS else text)
    return ", ".join(out) if out else "—"


def profile_table(con, table: str) -> list[dict]:
    total = con.execute(f"SELECT count(*) FROM stg.{table}").fetchone()[0]
    schema = con.execute(f"DESCRIBE stg.{table}").fetchall()
    rows = []
    for name, dtype, *_ in schema:
        nulls, distinct = con.execute(
            f'SELECT count(*) FILTER (WHERE "{name}" IS NULL), count(DISTINCT "{name}") '
            f"FROM stg.{table}"
        ).fetchone()
        rows.append(
            {
                "column": name,
                "type": dtype,
                "nulls": nulls,
                "null_pct": (nulls / total * 100) if total else 0.0,
                "distinct": distinct,
                "samples": sample_values(con, table, name),
            }
        )
    return rows


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found. Run src/ingest.py and src/build.py first.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    lines: list[str] = [
        "# Data dictionary — staging layer",
        "",
        f"Generated from `data/olist.duckdb` on {date.today().isoformat()} by "
        "`src/profile_columns.py`. Every figure below is the output of a query run "
        "at generation time; nothing here is transcribed by hand.",
        "",
        "Column names are the **staged** names. Where a staged name differs from the "
        "source CSV column, the source name is given in the notes so lineage stays "
        "traceable.",
        "",
    ]

    for table, (grain, key) in GRAIN.items():
        total = con.execute(f"SELECT count(*) FROM stg.{table}").fetchone()[0]
        lines += [
            f"## `stg.{table}`",
            "",
            f"- **Grain**: {grain}",
            f"- **Key**: `{key}`",
            f"- **Rows**: {total:,}",
            "",
            "| column | type | nulls | null % | distinct | sample values |",
            "|---|---|---:|---:|---:|---|",
        ]
        for row in profile_table(con, table):
            lines.append(
                f"| `{row['column']}` | {row['type']} | {row['nulls']:,} | "
                f"{row['null_pct']:.1f}% | {row['distinct']:,} | {row['samples']} |"
            )
        lines.append("")

    lines += [
        "## Renamed columns",
        "",
        "| staged name | source column | reason |",
        "|---|---|---|",
        "| `name_length` | `product_name_lenght` | source misspelling |",
        "| `description_length` | `product_description_lenght` | source misspelling |",
        "| `item_price` | `price` | disambiguates item value from payment value |",
        "| `purchased_at` … `estimated_delivery_at` | `order_*_timestamp` / `order_*_date` | consistent `_at` suffix for timestamps |",
        "| `customer_zip_prefix` | `customer_zip_code_prefix` | brevity; kept as text to preserve leading zeros |",
        "",
    ]
    con.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
