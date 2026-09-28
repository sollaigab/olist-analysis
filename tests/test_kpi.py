"""Reconciliation tests for the mart and KPI layers.

These answer the first question anyone asks: does this number still add up to
the source?

A join that multiplies amounts is the usual way an e-commerce analysis goes
wrong, and it's silent - the chart renders, the trend looks fine, the total is
just too big.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

# Source-of-truth totals, measured from stg on the 2026-09-28 load.
TOTAL_ITEMS_VALUE = Decimal("13591643.70")
TOTAL_FREIGHT_VALUE = Decimal("2251909.54")
TOTAL_PAYMENTS_VALUE = Decimal("16008872.12")

EXPECTED_ORDERS = 99_441
EXPECTED_ITEM_LINES = 112_650


# ---------------------------------------------------------------------------
# Grain: the marts must not have multiplied anything
# ---------------------------------------------------------------------------

def test_fct_orders_is_one_row_per_order(scalar):
    assert scalar("SELECT count(*) FROM mart.fct_orders") == EXPECTED_ORDERS
    assert scalar("SELECT count(DISTINCT order_id) FROM mart.fct_orders") == EXPECTED_ORDERS


def test_fct_order_items_keeps_item_grain(scalar):
    assert scalar("SELECT count(*) FROM mart.fct_order_items") == EXPECTED_ITEM_LINES
    duplicates = scalar(
        "SELECT count(*) - count(DISTINCT (order_id, order_item_id)) FROM mart.fct_order_items"
    )
    assert duplicates == 0


def test_every_item_line_survived_the_joins(scalar):
    """A LEFT JOIN that silently behaves like an INNER JOIN would drop lines here."""
    lost = scalar(
        "SELECT count(*) FROM stg.order_items i "
        "WHERE NOT EXISTS (SELECT 1 FROM mart.fct_order_items f "
        "WHERE f.order_id = i.order_id AND f.order_item_id = i.order_item_id)"
    )
    assert lost == 0


# ---------------------------------------------------------------------------
# Value conservation: the same money, counted once, at every layer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "relation,column,expected",
    [
        ("stg.order_items", "item_price", TOTAL_ITEMS_VALUE),
        ("int.items_by_order", "items_value", TOTAL_ITEMS_VALUE),
        ("mart.fct_orders", "items_value", TOTAL_ITEMS_VALUE),
        ("mart.fct_order_items", "item_price", TOTAL_ITEMS_VALUE),
        ("stg.order_items", "freight_value", TOTAL_FREIGHT_VALUE),
        ("int.items_by_order", "freight_value", TOTAL_FREIGHT_VALUE),
        ("mart.fct_orders", "freight_value", TOTAL_FREIGHT_VALUE),
        ("mart.fct_order_items", "freight_value", TOTAL_FREIGHT_VALUE),
        ("stg.order_payments", "payment_value", TOTAL_PAYMENTS_VALUE),
        ("int.payments_by_order", "payments_value", TOTAL_PAYMENTS_VALUE),
        ("mart.fct_orders", "payments_value", TOTAL_PAYMENTS_VALUE),
    ],
)
def test_totals_are_conserved_across_layers(scalar, relation, column, expected):
    actual = scalar("SELECT sum({}) FROM {}".format(column, relation))
    assert Decimal(str(actual)) == expected, (
        "{}.{} = {}, expected {}. Higher means a join multiplied rows; "
        "lower means rows were lost.".format(relation, column, actual, expected)
    )


def test_items_value_and_payments_value_are_not_interchangeable(scalar):
    """They differ by roughly 2.4M. Anything treating them as one number is wrong."""
    items = Decimal(str(scalar("SELECT sum(items_plus_freight) FROM mart.fct_orders")))
    payments = Decimal(str(scalar("SELECT sum(payments_value) FROM mart.fct_orders")))
    assert items != payments


# ---------------------------------------------------------------------------
# KPI views: denominators must be the ones the definitions claim
# ---------------------------------------------------------------------------

def test_monthly_sales_reconciles_to_the_filtered_mart(scalar):
    from_view = scalar("SELECT sum(items_value) FROM mart.kpi_sales_monthly")
    from_mart = scalar(
        "SELECT sum(items_value) FROM mart.fct_orders "
        "WHERE is_sale_eligible AND in_analysis_window"
    )
    assert Decimal(str(from_view)) == Decimal(str(from_mart))


def test_monthly_sales_covers_a_complete_month_range(con):
    months = [
        str(row[0])
        for row in con.execute(
            "SELECT purchase_month FROM mart.kpi_sales_monthly ORDER BY 1"
        ).fetchall()
    ]
    assert len(months) == 20, "expected 20 months in 2017-01..2018-08, got {}".format(len(months))
    assert months[0] == "2017-01-01"
    assert months[-1] == "2018-08-01"


def test_state_view_partitions_the_measurable_orders_exactly(scalar):
    """Every measurable order appears in exactly one state group."""
    view_total = scalar("SELECT sum(n_orders) FROM mart.kpi_delay_by_state")
    mart_total = scalar(
        "SELECT count(*) FROM mart.fct_orders "
        "WHERE has_delivery_measurement AND in_analysis_window"
    )
    assert view_total == mart_total


def test_category_view_overcounts_orders_on_purpose(scalar):
    """Multi-category orders count once per category; that must stay modest."""
    view_total = scalar("SELECT sum(n_orders) FROM mart.kpi_delay_by_category")
    distinct_orders = scalar(
        "SELECT count(DISTINCT order_id) FROM mart.fct_order_items "
        "WHERE has_delivery_measurement AND in_analysis_window"
    )
    assert view_total <= distinct_orders * 2, (
        "category expansion looks like a fan-out, not multi-category orders"
    )


def test_delay_buckets_partition_the_reviewed_orders(scalar):
    bucket_total = scalar("SELECT sum(n_orders) FROM mart.kpi_reviews_by_delay_bucket")
    expected = scalar(
        "SELECT count(*) FROM mart.fct_orders "
        "WHERE has_delivery_measurement AND has_review AND in_analysis_window"
    )
    assert bucket_total == expected


def test_punctuality_split_partitions_the_same_population(scalar):
    split_total = scalar("SELECT sum(n_orders) FROM mart.kpi_reviews_by_punctuality")
    expected = scalar(
        "SELECT count(*) FROM mart.fct_orders "
        "WHERE has_delivery_measurement AND has_review AND in_analysis_window"
    )
    assert split_total == expected


def test_late_flag_agrees_with_delay_days(scalar):
    """is_late and delay_days must never contradict each other."""
    contradictions = scalar(
        "SELECT count(*) FROM mart.fct_orders WHERE has_delivery_measurement "
        "AND ((is_late AND delay_days <= 0) OR (NOT is_late AND delay_days > 0))"
    )
    assert contradictions == 0


def test_no_kpi_view_reports_a_group_without_its_size(con):
    """A rate without an n is unquotable, so every KPI view exposes an n_ column."""
    views = [
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'mart' AND table_name LIKE 'kpi_%'"
        ).fetchall()
    ]
    assert views, "no KPI views found"
    for view in views:
        if view == "kpi_definitions":
            continue
        columns = [row[0] for row in con.execute("DESCRIBE mart.{}".format(view)).fetchall()]
        assert any(c.startswith("n_") for c in columns), "mart.{} reports no group size".format(view)


def test_every_kpi_definition_states_a_filter_and_a_denominator(con):
    incomplete = con.execute(
        "SELECT kpi FROM mart.kpi_definitions "
        "WHERE filter_applied IS NULL OR trim(filter_applied) = '' "
        "OR denominator IS NULL OR trim(denominator) = '' "
        "OR caveat IS NULL OR trim(caveat) = ''"
    ).fetchall()
    assert incomplete == [], "KPIs missing a filter, denominator or caveat: {}".format(incomplete)


def test_excluded_orders_are_actually_excluded(scalar):
    """Cancellations must not reach the sales KPI, and neither must undated deliveries."""
    leaked_cancellations = scalar(
        "SELECT count(*) FROM mart.fct_orders "
        "WHERE is_sale_eligible AND order_status IN ('canceled', 'unavailable')"
    )
    assert leaked_cancellations == 0

    undated = scalar(
        "SELECT count(*) FROM mart.fct_orders "
        "WHERE has_delivery_measurement AND delivered_customer_at IS NULL"
    )
    assert undated == 0
