"""Run the real SQL pipeline against synthetic data and assert its invariants.

These tests need no licensed data, so they run in CI on every push. They check
properties that must hold for ANY input — grain, conservation, correct handling
of each defect shape — rather than facts about Olist, which live in
`test_grain.py`, `test_kpi.py` and `test_report_figures.py` and are skipped when
the real database is absent.

The fixture is built by `tests/synthetic.py` and is clearly labelled as
fabricated. It is loaded through `src/ingest.py` and transformed by
`src/build.py`, so what is tested here is the shipped pipeline, not a
test-only imitation of it.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
import ingest  # noqa: E402
from synthetic import EXPECTED, write_fixture  # noqa: E402


@pytest.fixture(scope="module")
def synthetic_con(tmp_path_factory):
    """Build the whole model from synthetic CSVs, once for this module."""
    workdir = tmp_path_factory.mktemp("synthetic")
    raw_dir = write_fixture(workdir / "raw")
    db_path = workdir / "synthetic.duckdb"

    ingest.ingest(db_path=db_path, raw_dir=raw_dir, quiet=True)
    build.main(db_path=db_path, quiet=True)

    connection = duckdb.connect(str(db_path), read_only=True)
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def q(synthetic_con):
    def _q(sql: str):
        return synthetic_con.execute(sql).fetchone()

    return _q


# ---------------------------------------------------------------------------
# The pipeline runs at all
# ---------------------------------------------------------------------------

def test_every_sql_file_executes(synthetic_con):
    """A build failure on any layer surfaces here, on every CI run."""
    relations = synthetic_con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema IN ('raw','stg','qa','int','mart')"
    ).fetchone()[0]
    assert relations >= 25, f"only {relations} relations built; a layer is missing"


def test_raw_row_counts_match_the_fixture(q):
    assert q("SELECT count(*) FROM raw.orders")[0] == EXPECTED["orders"]
    assert q("SELECT count(*) FROM raw.order_items")[0] == EXPECTED["order_items"]
    assert q("SELECT count(*) FROM raw.order_payments")[0] == EXPECTED["order_payments"]
    assert q("SELECT count(*) FROM raw.order_reviews")[0] == EXPECTED["order_reviews"]


# ---------------------------------------------------------------------------
# Grain and conservation: the properties the whole design exists to guarantee
# ---------------------------------------------------------------------------

def test_fct_orders_never_multiplies_orders(q):
    rows, keys = q("SELECT count(*), count(DISTINCT order_id) FROM mart.fct_orders")
    assert rows == keys == EXPECTED["orders"], (
        "fct_orders gained or lost rows. With a multi-item, a multi-payment and a "
        "multi-review order all present in the fixture, this is the fan-out test."
    )


def test_item_grain_is_preserved(q):
    rows, keys = q(
        "SELECT count(*), count(DISTINCT (order_id, order_item_id)) FROM mart.fct_order_items"
    )
    assert rows == keys == EXPECTED["order_items"]


@pytest.mark.parametrize(
    "relation,column,expected_key",
    [
        ("stg.order_items", "item_price", "items_value"),
        ("int.items_by_order", "items_value", "items_value"),
        ("mart.fct_orders", "items_value", "items_value"),
        ("mart.fct_order_items", "item_price", "items_value"),
        ("stg.order_items", "freight_value", "freight_value"),
        ("mart.fct_orders", "freight_value", "freight_value"),
        ("stg.order_payments", "payment_value", "payments_value"),
        ("mart.fct_orders", "payments_value", "payments_value"),
    ],
)
def test_money_is_conserved_through_every_layer(q, relation, column, expected_key):
    total = q(f"SELECT sum({column}) FROM {relation}")[0]
    assert Decimal(str(total)) == Decimal(str(EXPECTED[expected_key]))


# ---------------------------------------------------------------------------
# Each defect shape is handled the way the model claims
# ---------------------------------------------------------------------------

def test_customer_id_and_unique_id_are_not_the_same_thing(q):
    ids, people = q(
        "SELECT count(DISTINCT customer_id), count(DISTINCT customer_unique_id) FROM stg.customers"
    )
    assert ids == EXPECTED["customers"]
    assert people == EXPECTED["distinct_people"]
    assert people < ids


def test_multiple_reviews_collapse_to_the_most_recent(q):
    rows = q("SELECT count(*) FROM int.reviews_by_order WHERE order_id = 'o-2'")[0]
    assert rows == 1, "o-2 carries two reviews and must collapse to one row"
    score, n_reviews, spread = q(
        "SELECT review_score, n_reviews, score_spread FROM int.reviews_by_order "
        "WHERE order_id = 'o-2'"
    )
    assert score == 1, "the later review (score 1) must win, not the earlier 3"
    assert n_reviews == 2
    assert spread == 2, "the disagreement must remain visible after the collapse"


def test_review_id_is_not_treated_as_a_key(q):
    """rev-shared is attached to two orders; both must survive."""
    orders = q(
        "SELECT count(DISTINCT order_id) FROM stg.order_reviews WHERE review_id = 'rev-shared'"
    )[0]
    assert orders == 2
    kept = q(
        "SELECT count(*) FROM int.reviews_by_order WHERE review_id = 'rev-shared'"
    )[0]
    assert kept == 2, "collapsing by review_id instead of order_id would drop one order"


def test_split_payments_do_not_fan_out(q):
    lines, value = q(
        "SELECT n_payment_lines, payments_value FROM int.payments_by_order WHERE order_id = 'o-7'"
    )
    assert lines == 2
    assert Decimal(str(value)) == Decimal("25.00")


def test_cancelled_order_without_items_is_excluded_from_the_aov_denominator(q):
    assert q("SELECT items_value FROM mart.fct_orders WHERE order_id = 'o-4'")[0] is None
    assert q("SELECT is_sale_eligible FROM mart.fct_orders WHERE order_id = 'o-4'")[0] is False
    with_items = q("SELECT count(*) FROM mart.fct_orders WHERE items_value IS NOT NULL")[0]
    assert with_items == EXPECTED["orders_with_items"]


def test_delivered_without_a_date_is_excluded_from_delay_kpis(q):
    status, measurable = q(
        "SELECT order_status, has_delivery_measurement FROM mart.fct_orders WHERE order_id = 'o-5'"
    )
    assert status == "delivered"
    assert measurable is False, "no delivery timestamp means the delay is unmeasurable"


def test_delivery_on_the_promised_day_counts_as_on_time(q):
    """o-6 was delivered at 18:00 on the promised date, which is midnight."""
    is_late, delay = q(
        "SELECT is_late, delay_days FROM mart.fct_orders WHERE order_id = 'o-6'"
    )
    assert delay == 0
    assert is_late is False, (
        "comparing timestamps instead of dates would mark this 18 hours late"
    )


def test_both_sides_of_the_late_flag_are_exercised(q):
    late, early = q(
        "SELECT count(*) FILTER (WHERE is_late), count(*) FILTER (WHERE NOT is_late) "
        "FROM mart.fct_orders WHERE has_delivery_measurement"
    )
    assert late >= 1 and early >= 1


def test_late_flag_never_contradicts_delay_days(q):
    contradictions = q(
        "SELECT count(*) FROM mart.fct_orders WHERE has_delivery_measurement "
        "AND ((is_late AND delay_days <= 0) OR (NOT is_late AND delay_days > 0))"
    )[0]
    assert contradictions == 0


def test_multi_seller_order_is_flagged(q):
    sellers, flagged = q(
        "SELECT n_sellers, is_multi_seller FROM mart.fct_orders WHERE order_id = 'o-3'"
    )
    assert sellers == 2
    assert flagged is True


def test_zip_prefix_keeps_its_leading_zero(q):
    prefix = q("SELECT customer_zip_prefix FROM stg.customers WHERE customer_id = 'c-2'")[0]
    assert prefix == "20040"
    sp = q("SELECT customer_zip_prefix FROM stg.customers WHERE customer_id = 'c-5'")[0]
    assert sp == "01037", "casting a zip prefix to INTEGER would make this 1037"


def test_geolocation_collapses_to_one_row_per_prefix(q):
    source, staged = q(
        "SELECT (SELECT count(*) FROM raw.geolocation), (SELECT count(*) FROM stg.geolocation)"
    )
    assert staged == EXPECTED["zip_prefixes"]
    assert staged < source


def test_missing_and_untranslated_categories_are_handled(q):
    unknown = q(
        "SELECT count(*) FROM mart.fct_order_items WHERE category = 'unknown'"
    )[0]
    assert unknown >= 1, "a product with no category must land in the unknown bucket"
    untranslated = q(
        "SELECT count(*) FROM mart.fct_order_items WHERE category_untranslated"
    )[0]
    assert untranslated >= 1, "an untranslated category must keep its Portuguese name"


# ---------------------------------------------------------------------------
# The quality and KPI layers keep their contracts
# ---------------------------------------------------------------------------

def test_quality_layer_finds_the_planted_defects(synthetic_con):
    rules = dict(
        synthetic_con.execute("SELECT rule, n_rows FROM qa.business_checks").fetchall()
    )
    assert rules["delivered orders missing a delivery date"] == 1
    assert rules["orders carrying more than one review"] == 1
    assert rules["orders fulfilled by more than one seller"] == 1
    assert rules["review_id reused across different orders"] == 1
    assert rules["item price <= 0"] == 1
    assert rules["repeat customers (customer_unique_id with >1 order)"] == 1


def test_no_cast_destroyed_data_in_the_fixture(synthetic_con):
    failures = synthetic_con.execute(
        "SELECT column_checked, failed_casts FROM qa.cast_audit WHERE failed_casts > 0"
    ).fetchall()
    assert failures == []


def test_every_kpi_view_still_exposes_a_group_size(synthetic_con):
    views = [
        row[0]
        for row in synthetic_con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'mart' AND table_name LIKE 'kpi_%'"
        ).fetchall()
    ]
    assert views
    for view in views:
        if view == "kpi_definitions":
            continue
        columns = [
            row[0] for row in synthetic_con.execute(f"DESCRIBE mart.{view}").fetchall()
        ]
        assert any(c.startswith("n_") for c in columns), f"mart.{view} reports no group size"


def test_wilson_interval_brackets_the_point_estimate(synthetic_con):
    """Property test: for any group, lower <= rate <= upper, and both in [0,100]."""
    rows = synthetic_con.execute(
        "SELECT customer_state, late_rate_pct, ci_lower_pct, ci_upper_pct "
        "FROM mart.kpi_state_late_rate_ci"
    ).fetchall()
    assert rows, "the CI view produced no rows"
    for state, rate, lower, upper in rows:
        assert 0.0 <= lower <= rate <= upper <= 100.0, f"{state}: {lower} / {rate} / {upper}"


def test_wilson_interval_is_wider_for_smaller_groups(synthetic_con):
    """The whole point of the interval: less data, less certainty."""
    rows = synthetic_con.execute(
        "SELECT n_orders, ci_width_pp FROM mart.kpi_state_late_rate_ci "
        "WHERE n_orders > 0 ORDER BY n_orders"
    ).fetchall()
    if len(rows) < 2 or rows[0][0] == rows[-1][0]:
        pytest.skip("fixture has no spread in group sizes")
    assert rows[0][1] >= rows[-1][1]


def test_retention_marks_censored_cohorts(synthetic_con):
    """A cohort without a full 90-day window must be flagged, not silently shown."""
    columns = [
        row[0]
        for row in synthetic_con.execute("DESCRIBE mart.kpi_cohort_retention_90d").fetchall()
    ]
    assert "is_complete" in columns
    rows = synthetic_con.execute(
        "SELECT n_new_customers, n_repeated_within_90d FROM mart.kpi_cohort_retention_90d"
    ).fetchall()
    for new_customers, repeated in rows:
        assert repeated <= new_customers, "more repeaters than customers is impossible"
