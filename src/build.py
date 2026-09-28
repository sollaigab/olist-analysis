"""Run the SQL layers in order against the local DuckDB database.

Layers execute in lexical order of directory then filename, which is why the
directories are numbered. Each file is idempotent (CREATE OR REPLACE), so the
whole model can be rebuilt at any time without dropping the database.

Usage:
    python src/build.py              # run every layer
    python src/build.py 00 20        # run only layers whose dir starts with these
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH, SCHEMAS, SQL_DIR  # noqa: E402


def sql_files(prefixes: list[str] | None = None) -> list[Path]:
    dirs = sorted(d for d in SQL_DIR.iterdir() if d.is_dir())
    if prefixes:
        dirs = [d for d in dirs if any(d.name.startswith(p) for p in prefixes)]
    return [f for d in dirs for f in sorted(d.glob("*.sql"))]


def main(prefixes: list[str] | None = None) -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found. Run src/ingest.py first.")

    con = duckdb.connect(str(DB_PATH))
    for schema in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    files = sql_files(prefixes)
    if not files:
        raise SystemExit("No .sql files matched.")

    current_dir = None
    for path in files:
        if path.parent.name != current_dir:
            current_dir = path.parent.name
            print(f"\n[{current_dir}]")
        started = time.perf_counter()
        try:
            con.execute(path.read_text(encoding="utf-8"))
        except Exception as exc:
            con.close()
            raise SystemExit(f"  FAILED {path.name}\n{exc}") from exc
        print(f"  ok  {path.name:<34} {time.perf_counter() - started:6.2f}s")

    con.close()
    print(f"\nBuild complete: {len(files)} file(s).")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
