"""Export dashboard-ready aggregates to dashboard/exports/.

Only aggregates leave the database. The raw dataset is licensed CC BY-NC-SA and
is not redistributed; these files contain group-level counts and sums, which is
also all a dashboard needs.

Every export is reconciled against the database immediately after it is written:
the CSV is read back and its totals compared to the source view. An export that
does not reconcile aborts the run rather than quietly shipping a wrong file to
Power BI, which is exactly the failure that makes a dashboard untrustworthy.

Usage:
    python src/export_bi.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH, EXPORT_DIR  # noqa: E402

# (filename, source relation, column to reconcile on or None for a row count)
EXPORTS: list[tuple[str, str, str | None]] = [
    ("kpi_definitions.csv", "mart.kpi_definitions", None),
    ("sales_monthly.csv", "mart.kpi_sales_monthly", "items_value"),
    ("delay_by_state.csv", "mart.kpi_delay_by_state", "n_orders"),
    ("delay_by_category.csv", "mart.kpi_delay_by_category", "n_orders"),
    ("category_priority.csv", "mart.kpi_category_priority", "n_late_orders"),
    ("state_priority.csv", "mart.kpi_state_priority", "n_late_orders"),
    ("reviews_by_punctuality.csv", "mart.kpi_reviews_by_punctuality", "n_orders"),
    ("reviews_by_delay_bucket.csv", "mart.kpi_reviews_by_delay_bucket", "n_orders"),
    ("review_coverage_monthly.csv", "mart.kpi_review_coverage", "n_reviewed"),
]

# Extra aggregates that are shaped for charts rather than for reading.
EXTRA_QUERIES: dict[str, str] = {
    # Delay distribution, trimmed for readability: the tails are reported as
    # counts in the report rather than drawn, so the chart is not 95% whitespace.
    "delay_distribution.csv": """
        SELECT delay_days, count(*) AS n_orders
        FROM mart.fct_orders
        WHERE has_delivery_measurement AND in_analysis_window
          AND delay_days BETWEEN -40 AND 40
        GROUP BY delay_days
        ORDER BY delay_days
    """,
    # Late rate by month, to show whether the delay problem is growing.
    "late_rate_monthly.csv": """
        SELECT purchase_month,
               count(*)                        AS n_orders,
               count(*) FILTER (WHERE is_late) AS n_late_orders,
               round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 2) AS late_rate_pct,
               median(delay_days)              AS median_delay_days,
               round(avg(review_score), 3)     AS mean_review_score,
               count(*) FILTER (WHERE has_review) AS n_reviewed_orders
        FROM mart.fct_orders
        WHERE has_delivery_measurement AND in_analysis_window
        GROUP BY purchase_month
        ORDER BY purchase_month
    """,
    # Payment mix, used on the overview page.
    "payment_mix_monthly.csv": """
        SELECT purchase_month,
               dominant_payment_type,
               count(*)          AS n_orders,
               sum(items_value)  AS items_value,
               round(avg(max_installments), 2) AS avg_max_installments
        FROM mart.fct_orders
        WHERE is_sale_eligible AND in_analysis_window
          AND dominant_payment_type IS NOT NULL
        GROUP BY purchase_month, dominant_payment_type
        ORDER BY purchase_month, n_orders DESC
    """,
    # Seller-state view of lateness. Deliberately seller-level for LOGISTICS
    # only: review scores are NOT attributed to sellers here, because 1,278
    # orders involve more than one seller and the review belongs to the order.
    "delay_by_seller_state.csv": """
        SELECT seller_state,
               count(DISTINCT order_id)                        AS n_orders,
               count(DISTINCT order_id) FILTER (WHERE is_late) AS n_late_orders,
               round(100.0 * count(DISTINCT order_id) FILTER (WHERE is_late)
                           / nullif(count(DISTINCT order_id), 0), 2) AS late_rate_pct,
               median(delay_days)                              AS median_delay_days,
               sum(item_price)                                 AS items_value
        FROM mart.fct_order_items
        WHERE has_delivery_measurement AND in_analysis_window
          AND seller_state IS NOT NULL
        GROUP BY seller_state
        HAVING count(DISTINCT order_id) >= 100
        ORDER BY n_late_orders DESC
    """,
    # State x month, for a dashboard slicer that crosses geography and time.
    "late_rate_state_monthly.csv": """
        SELECT customer_state,
               purchase_month,
               count(*)                        AS n_orders,
               count(*) FILTER (WHERE is_late) AS n_late_orders,
               round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 2) AS late_rate_pct
        FROM mart.fct_orders
        WHERE has_delivery_measurement AND in_analysis_window
        GROUP BY customer_state, purchase_month
        HAVING count(*) >= 30
        ORDER BY customer_state, purchase_month
    """,
}


def reconcile(con, df: pd.DataFrame, relation: str, column: str | None) -> str:
    """Compare the written frame against the database. Raise on mismatch."""
    if column is None:
        expected = con.execute(f"SELECT count(*) FROM {relation}").fetchone()[0]
        actual = len(df)
        label = "row count"
    else:
        expected = con.execute(f"SELECT sum({column}) FROM {relation}").fetchone()[0]
        actual = df[column].sum()
        label = f"sum({column})"

    if expected is None:
        raise SystemExit(f"{relation}: reconciliation column {column} is all NULL")

    if abs(float(actual) - float(expected)) > 0.01:
        raise SystemExit(
            f"RECONCILIATION FAILED for {relation}\n"
            f"  {label} in database: {expected}\n"
            f"  {label} in CSV     : {actual}\n"
            "  The export does not match its source. Not shipping this file."
        )
    return f"{label} {float(expected):,.2f}"


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found. Run src/ingest.py and src/build.py first.")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)

    manifest: list[dict] = []
    print(f"{'file':<32} {'rows':>6}  reconciled on")
    print("-" * 74)

    for filename, relation, column in EXPORTS:
        df = con.execute(f"SELECT * FROM {relation}").df()
        path = EXPORT_DIR / filename
        df.to_csv(path, index=False, encoding="utf-8")
        # Read back from disk: this checks the file, not the DataFrame in memory.
        written = pd.read_csv(path)
        detail = reconcile(con, written, relation, column)
        print(f"{filename:<32} {len(df):>6}  {detail}")
        manifest.append(
            {"file": filename, "source": relation, "rows": len(df),
             "columns": len(df.columns), "reconciled_on": column or "row count"}
        )

    for filename, query in EXTRA_QUERIES.items():
        df = con.execute(query).df()
        path = EXPORT_DIR / filename
        df.to_csv(path, index=False, encoding="utf-8")
        written = pd.read_csv(path)
        if len(written) != len(df):
            raise SystemExit(f"{filename}: wrote {len(df)} rows, read back {len(written)}")
        print(f"{filename:<32} {len(df):>6}  row count {len(df)}")
        manifest.append(
            {"file": filename, "source": "ad-hoc query in src/export_bi.py",
             "rows": len(df), "columns": len(df.columns), "reconciled_on": "row count"}
        )

    manifest_df = pd.DataFrame(manifest)
    manifest_df.insert(0, "generated_on", date.today().isoformat())
    manifest_df.to_csv(EXPORT_DIR / "_manifest.csv", index=False, encoding="utf-8")

    con.close()
    total_rows = sum(entry["rows"] for entry in manifest)
    print("-" * 74)
    print(f"{len(manifest)} files, {total_rows:,} rows total, all reconciled.")
    print(f"Written to {EXPORT_DIR}")


if __name__ == "__main__":
    main()
