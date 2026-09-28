"""Grain, key and integrity assertions for the staging layer.

These tests encode the claims the data model makes. If a claim is false, the
suite fails here rather than producing a quietly wrong number in a dashboard.

Counts of *known* data defects are frozen as baselines: the goal is not to
pretend the defects are absent, but to detect the day their number changes.
"""

from __future__ import annotations

import pytest

# --- Row counts as loaded on 2026-09-28 from Kaggle olistbr/brazilian-ecommerce
BASELINE_ROWS = {
    "raw.orders": 99_441,
    "raw.order_items": 112_650,
    "raw.order_payments": 103_886,
    "raw.order_reviews": 99_224,
    "raw.customers": 99_441,
    "raw.sellers": 3_095,
    "raw.products": 32_951,
    "raw.category_translation": 71,
    "raw.geolocation": 1_000_163,
}

# (table, key expression) pairs that must be unique.
UNIQUE_KEYS = [
    ("stg.orders", "order_id"),
    ("stg.customers", "customer_id"),
    ("stg.order_items", "(order_id, order_item_id)"),
    ("stg.order_payments", "(order_id, payment_sequential)"),
    ("stg.products", "product_id"),
    ("stg.sellers", "seller_id"),
    ("stg.category_translation", "category_pt"),
    ("stg.geolocation", "zip_prefix"),
    # NOTE: stg.order_reviews.review_id is deliberately absent. It is NOT unique
    # (see test_review_id_is_not_a_primary_key) and treating it as a key would
    # be the bug this suite exists to prevent.
]

# Relationships whose orphan count must be exactly zero.
MUST_HAVE_NO_ORPHANS = [
    ("stg.order_items", "order_id", "stg.orders", "order_id"),
    ("stg.order_items", "product_id", "stg.products", "product_id"),
    ("stg.order_items", "seller_id", "stg.sellers", "seller_id"),
    ("stg.orders", "customer_id", "stg.customers", "customer_id"),
    ("stg.order_reviews", "order_id", "stg.orders", "order_id"),
    ("stg.order_payments", "order_id", "stg.orders", "order_id"),
]

# Known defects, frozen. A change here means the source data changed.
BASELINE_ANOMALIES = {
    "delivered orders missing a delivery date": 8,
    "delivery to customer earlier than handover to carrier": 23,
    "payment value <= 0": 9,
    "review_id reused across different orders": 789,
    "orders carrying more than one review": 547,
    "orders fulfilled by more than one seller": 1_278,
}


@pytest.mark.parametrize("table,expected", sorted(BASELINE_ROWS.items()))
def test_raw_row_counts_match_baseline(scalar, table, expected):
    assert scalar(f"SELECT count(*) FROM {table}") == expected


@pytest.mark.parametrize("table,key", UNIQUE_KEYS)
def test_declared_keys_are_unique(scalar, table, key):
    duplicates = scalar(
        f"SELECT count(*) - count(DISTINCT {key}) FROM {table}"
    )
    assert duplicates == 0, f"{table} has {duplicates} duplicate rows on {key}"


@pytest.mark.parametrize("child,child_key,parent,parent_key", MUST_HAVE_NO_ORPHANS)
def test_no_orphan_foreign_keys(scalar, child, child_key, parent, parent_key):
    orphans = scalar(
        f"SELECT count(*) FROM {child} c "
        f"WHERE NOT EXISTS (SELECT 1 FROM {parent} p WHERE p.{parent_key} = c.{child_key})"
    )
    assert orphans == 0, f"{orphans} rows in {child} reference a missing {parent}"


def test_no_cast_silently_destroyed_data(con):
    failures = con.execute(
        "SELECT column_checked, failed_casts FROM qa.cast_audit WHERE failed_casts > 0"
    ).fetchall()
    assert failures == [], f"TRY_CAST nulled out real values: {failures}"


def test_review_id_is_not_a_primary_key(scalar):
    """Documents a real property of the source rather than asserting it away."""
    reused = scalar(
        "SELECT count(*) FROM (SELECT review_id FROM stg.order_reviews "
        "GROUP BY 1 HAVING count(DISTINCT order_id) > 1)"
    )
    assert reused > 0, (
        "review_id became unique — the source changed; revisit the review grain "
        "and the (review_id, order_id) key before trusting review KPIs"
    )


def test_customer_id_and_customer_unique_id_differ(scalar):
    """If these ever match, every customer-count KPI in the project is wrong."""
    ids = scalar("SELECT count(DISTINCT customer_id) FROM stg.customers")
    people = scalar("SELECT count(DISTINCT customer_unique_id) FROM stg.customers")
    assert people < ids, "customer_unique_id must collapse repeat buyers"


def test_zip_prefixes_keep_leading_zeros(scalar):
    """A zip prefix cast to INTEGER loses '01037'. Guard against that."""
    padded = scalar(
        "SELECT count(*) FROM stg.customers WHERE customer_zip_prefix LIKE '0%'"
    )
    assert padded > 0
    assert scalar("SELECT count(*) FROM stg.customers WHERE length(customer_zip_prefix) <> 5") == 0


def test_geolocation_is_deduplicated_to_one_row_per_prefix(scalar):
    raw_rows = scalar("SELECT count(*) FROM raw.geolocation")
    staged_rows = scalar("SELECT count(*) FROM stg.geolocation")
    assert staged_rows < raw_rows / 10, "geolocation was not collapsed; joins will fan out"


@pytest.mark.parametrize("rule,expected", sorted(BASELINE_ANOMALIES.items()))
def test_known_anomalies_match_frozen_baseline(scalar, rule, expected):
    actual = scalar(
        f"SELECT n_rows FROM qa.business_checks WHERE rule = '{rule}'"
    )
    assert actual == expected, (
        f"'{rule}' moved from {expected} to {actual}. The source data changed; "
        "re-read the quality report before trusting any downstream number."
    )


def test_rules_that_must_be_zero_are_zero(con):
    violations = con.execute(
        """
        SELECT rule, n_rows FROM qa.business_checks
        WHERE status = 'FAIL' AND n_rows > 0
          AND rule NOT IN (
            'delivered orders missing a delivery date',
            'delivery to customer earlier than handover to carrier'
          )
        """
    ).fetchall()
    assert violations == [], f"unexpected rule violations: {violations}"
