"""Step 1 of the pipeline: get the CSVs, load them into DuckDB untouched.

Design decision: every column lands in the `raw` schema as VARCHAR.
DuckDB's type sniffer is good, but a sniffer that guesses wrong turns a data
quality problem into a silent data loss problem (a malformed timestamp becomes
NULL and nobody notices). Casting happens explicitly in sql/00_staging/, where
it is visible, reviewable and testable.

Usage:
    python src/ingest.py --download    # fetch from Kaggle, then load
    python src/ingest.py               # load whatever is already in data/raw
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH, KAGGLE_DATASET, RAW_DIR, SCHEMAS, SOURCE_FILES  # noqa: E402

MANUAL_INSTRUCTIONS = f"""
Kaggle credentials not found.

Option A - API (repeatable, preferred):
  1. kaggle.com -> Settings -> API -> "Create New Token"
  2. Save the downloaded kaggle.json to:
       {Path.home() / '.kaggle' / 'kaggle.json'}
  3. Re-run: python src/ingest.py --download

Option B - manual:
  1. Download the dataset archive from the Kaggle dataset page
       ({KAGGLE_DATASET})
  2. Unzip all 9 CSV files into:
       {RAW_DIR}
  3. Run: python src/ingest.py
"""


def have_kaggle_credentials() -> bool:
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True
    return (Path.home() / ".kaggle" / "kaggle.json").exists()


def download() -> None:
    """Fetch and unzip the dataset into data/raw."""
    if not have_kaggle_credentials():
        raise SystemExit(MANUAL_INSTRUCTIONS)

    from kaggle.api.kaggle_api_extended import KaggleApi

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    api = KaggleApi()
    api.authenticate()
    print(f"Downloading {KAGGLE_DATASET} -> {RAW_DIR}")
    api.dataset_download_files(KAGGLE_DATASET, path=str(RAW_DIR), quiet=False)

    for archive in RAW_DIR.glob("*.zip"):
        print(f"Unzipping {archive.name}")
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(RAW_DIR)
        archive.unlink()


def check_files() -> list[str]:
    """Return the list of expected files that are missing from data/raw."""
    return [name for name in SOURCE_FILES if not (RAW_DIR / name).exists()]


def ingest() -> None:
    missing = check_files()
    if missing:
        raise SystemExit(
            f"Missing {len(missing)} expected file(s) in {RAW_DIR}:\n  "
            + "\n  ".join(missing)
            + "\n\nRun with --download, or place the files manually."
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    for schema in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    print(f"\n{'table':<22} {'rows':>10} {'cols':>6}")
    print("-" * 40)
    for filename, table in SOURCE_FILES.items():
        path = (RAW_DIR / filename).as_posix()
        con.execute(f"DROP TABLE IF EXISTS raw.{table}")
        con.execute(
            f"""
            CREATE TABLE raw.{table} AS
            SELECT * FROM read_csv(
                '{path}',
                all_varchar = true,   -- no type guessing; cast later, explicitly
                header      = true,
                sample_size = -1      -- scan the whole file, not a sample
            )
            """
        )
        rows = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE raw.{table}").fetchall())
        print(f"{table:<22} {rows:>10,} {cols:>6}")

    con.close()
    print(f"\nDatabase written to {DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Olist CSVs into DuckDB.")
    parser.add_argument("--download", action="store_true", help="fetch from Kaggle first")
    args = parser.parse_args()

    if args.download:
        download()
    ingest()
