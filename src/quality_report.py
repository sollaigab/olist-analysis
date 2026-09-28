"""Render the qa.* tables into reports/quality_report.md.

Same principle as the data dictionary: the document is a view over the
database, regenerated on demand, never edited by hand.

Usage:
    python src/quality_report.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH, PROJECT_ROOT  # noqa: E402

OUT_PATH = PROJECT_ROOT / "reports" / "quality_report.md"

SECTIONS = [
    ("Cast audit", "qa.cast_audit",
     "A non-zero `failed_casts` means an explicit cast turned a real value into "
     "NULL. `blank_source` counts values that were already absent in the CSV."),
    ("Declared keys and cardinality", "qa.key_checks",
     "`duplicate_rows` is expected to be 0 where the expectation says *unique*, "
     "and greater than 0 where it says *NOT unique* — a one-to-many relationship "
     "that turned out to be one-to-one would be just as much of a surprise."),
    ("Referential integrity", "qa.referential_checks",
     "Orphans are counted, not assumed away. Rows noted *must be 0* are hard "
     "failures; the rest are documented characteristics of the dataset."),
    ("Business rules", "qa.business_checks",
     "`FAIL` contradicts the model and is excluded or flagged downstream. "
     "`INFO` is a genuine property of the data that shapes how KPIs are built."),
]


def to_markdown_table(con, relation: str) -> list[str]:
    df = con.execute(f"SELECT * FROM {relation}").df()
    header = "| " + " | ".join(df.columns) + " |"
    divider = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = [
        "| " + " | ".join(
            f"{v:,}" if isinstance(v, (int,)) and not isinstance(v, bool) else str(v)
            for v in record
        ) + " |"
        for record in df.itertuples(index=False, name=None)
    ]
    return [header, divider, *rows]


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found. Run src/ingest.py and src/build.py first.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    lines = [
        "# Data quality report",
        "",
        f"Generated from `data/olist.duckdb` on {date.today().isoformat()} by "
        "`src/quality_report.py`. Regenerate after any change to `sql/00_staging/` "
        "or `sql/10_quality/`.",
        "",
        "The counts below are asserted in `tests/test_grain.py`: known defects are "
        "frozen as a baseline so the suite fails when the *data* changes, rather "
        "than staying permanently red.",
        "",
    ]
    for title, relation, note in SECTIONS:
        lines += [f"## {title}", "", note, ""] + to_markdown_table(con, relation) + [""]
    con.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
