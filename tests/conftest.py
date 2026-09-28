"""Shared fixtures: one read-only connection for the whole test session."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import DB_PATH  # noqa: E402


@pytest.fixture(scope="session")
def con():
    if not DB_PATH.exists():
        pytest.skip(f"{DB_PATH} not found — run src/ingest.py and src/build.py first")
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def scalar(con):
    def _scalar(sql: str):
        return con.execute(sql).fetchone()[0]

    return _scalar
