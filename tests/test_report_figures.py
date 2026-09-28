"""Assert the headline figures quoted in reports/report.md.

A written report drifts away from its data the moment either one is edited
without the other. These tests pin every number the report states in prose or in
a summary table, so the drift becomes a failing test instead of a wrong slide.

If one of these fails, exactly one of two things is true: the data changed, or
the report is now wrong. Both are worth stopping for.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

WINDOW = "is_sale_eligible AND in_analysis_window"
MEASURABLE = "has_delivery_measurement AND in_analysis_window"


# --------------------------------------------------------------------------
# Scope
# --------------------------------------------------------------------------

def test_analysis_window_population(scalar):
    assert scalar(f"SELECT count(*) FROM mart.fct_orders WHERE {WINDOW}") == 97_910
    assert scalar(f"SELECT count(*) FROM mart.fct_orders WHERE {MEASURABLE}") == 96_203


def test_window_money_totals(scalar):
    """The window totals, which are NOT the whole-dataset totals."""
    items = scalar(f"SELECT sum(items_value) FROM mart.fct_orders WHERE {WINDOW}")
    freight = scalar(f"SELECT sum(freight_value) FROM mart.fct_orders WHERE {WINDOW}")
    payments = scalar(f"SELECT sum(payments_value) FROM mart.fct_orders WHERE {WINDOW}")
    assert Decimal(str(items)) == Decimal("13449529.68")
    assert Decimal(str(freight)) == Decimal("2234177.06")
    assert Decimal(str(payments)) == Decimal("15687157.17")


# --------------------------------------------------------------------------
# Q1
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "month,orders,items_value,aov,avg_item_price,freight_pct",
    [
        ("2017-01-01", 787, "120098.27", "152.60", "126.02", "14.03"),
        ("2018-08-01", 6421, "848860.10", "132.20", "117.64", "17.45"),
    ],
)
def test_first_and_last_month(con, month, orders, items_value, aov, avg_item_price, freight_pct):
    row = con.execute(
        "SELECT n_orders, items_value, aov, avg_item_price, freight_pct_of_items "
        f"FROM mart.kpi_sales_monthly WHERE purchase_month = DATE '{month}'"
    ).fetchone()
    assert row[0] == orders
    assert Decimal(str(row[1])) == Decimal(items_value)
    assert Decimal(str(row[2])) == Decimal(aov)
    assert Decimal(str(row[3])) == Decimal(avg_item_price)
    assert Decimal(str(row[4])) == Decimal(freight_pct)


# --------------------------------------------------------------------------
# Q2
# --------------------------------------------------------------------------

def test_headline_late_rate(scalar):
    late = scalar(f"SELECT count(*) FILTER (WHERE is_late) FROM mart.fct_orders WHERE {MEASURABLE}")
    total = scalar(f"SELECT count(*) FROM mart.fct_orders WHERE {MEASURABLE}")
    assert late == 6_531
    assert round(100.0 * late / total, 2) == 6.79


def test_delay_distribution_statistics(con):
    row = con.execute(
        "SELECT median(delay_days), quantile_cont(delay_days, 0.9), "
        "quantile_cont(delay_days, 0.99), max(delay_days), median(delivery_days) "
        f"FROM mart.fct_orders WHERE {MEASURABLE}"
    ).fetchone()
    assert row[0] == -12, "median delay: the typical order arrives 12 days early"
    assert row[1] == -2
    assert row[2] == 18
    assert row[3] == 188
    assert row[4] == 10


def test_three_spike_months_carry_half_the_lateness(con):
    spikes = "purchase_month IN (DATE '2017-11-01', DATE '2018-02-01', DATE '2018-03-01')"
    row = con.execute(
        f"SELECT count(*) FILTER (WHERE {spikes}), "
        f"count(*) FILTER (WHERE {spikes} AND is_late), "
        f"count(*) FILTER (WHERE NOT ({spikes})), "
        f"count(*) FILTER (WHERE NOT ({spikes}) AND is_late) "
        f"FROM mart.fct_orders WHERE {MEASURABLE}"
    ).fetchone()
    spike_orders, spike_late, other_orders, other_late = row
    assert (spike_orders, spike_late) == (20_846, 3_158)
    assert (other_orders, other_late) == (75_357, 3_373)
    assert round(100.0 * spike_late / (spike_late + other_late), 1) == 48.4
    assert round(100.0 * spike_late / spike_orders, 2) == 15.15
    assert round(100.0 * other_late / other_orders, 2) == 4.48


def test_volume_correlates_only_moderately_with_lateness(scalar):
    """r = 0.51. The report must not upgrade this into an explanation."""
    r = scalar(
        "SELECT corr(n_orders, late_rate) FROM ("
        "  SELECT purchase_month, count(*) AS n_orders, "
        "         100.0 * count(*) FILTER (WHERE is_late) / count(*) AS late_rate "
        f"  FROM mart.fct_orders WHERE {MEASURABLE} GROUP BY 1)"
    )
    assert round(r, 2) == 0.51


@pytest.mark.parametrize(
    "state,orders,late,rate,excess",
    [
        ("RJ", 12_310, 1_495, 12.14, 659),
        ("BA", 3_253, 396, 12.17, 175),
        ("CE", 1_273, 176, 13.83, 90),
        ("ES", 1_992, 214, 10.74, 79),
        ("MA", 713, 125, 17.53, 77),
        ("AL", 396, 85, 21.46, 58),
        ("MG", 11_319, 519, 4.59, -249),
        ("SP", 40_399, 1_817, 4.50, -926),
    ],
)
def test_state_table(con, state, orders, late, rate, excess):
    row = con.execute(
        "SELECT n_orders, n_late_orders, late_rate_pct, excess_late_orders "
        f"FROM mart.kpi_state_priority WHERE customer_state = '{state}'"
    ).fetchone()
    assert row[0] == orders
    assert row[1] == late
    assert float(row[2]) == rate
    assert int(row[3]) == excess


def test_category_spread_at_volume(con):
    """The report's precise claim: among the 22 categories with >= 1,000 orders,
    none is more than 1.30pp WORSE than the national rate, and the full spread
    runs from -2.47pp to +1.30pp (late rates 4.32% to 8.09%).

    The asymmetry matters. An earlier draft said 'within 1.3 points', which was
    false in the favourable direction and was caught by this test.
    """
    row = con.execute(
        "SELECT count(*), min(rate_gap_pp), max(rate_gap_pp), "
        "min(late_rate_pct), max(late_rate_pct) "
        "FROM mart.kpi_category_priority WHERE n_orders >= 1000"
    ).fetchone()
    assert row[0] == 22
    assert float(row[1]) == -2.47
    assert float(row[2]) == 1.30
    assert float(row[3]) == 4.32
    assert float(row[4]) == 8.09


def test_variance_sits_downstream_of_carrier_handover(con):
    """Handover is flat across fast and slow states; transit is not."""
    rows = con.execute(
        "SELECT CASE WHEN late_rate_pct >= 12 THEN 'slow' ELSE 'fast' END AS band, "
        "avg(median_handover_days), avg(median_delivery_days) "
        "FROM mart.kpi_state_priority GROUP BY 1 ORDER BY 1"
    ).fetchall()
    bands = {row[0]: (float(row[1]), float(row[2])) for row in rows}
    handover_gap = abs(bands["slow"][0] - bands["fast"][0])
    delivery_gap = bands["slow"][1] - bands["fast"][1]
    assert handover_gap < 0.2, "handover is no longer flat; the report's claim needs revisiting"
    assert delivery_gap > 2.0


# --------------------------------------------------------------------------
# Q3
# --------------------------------------------------------------------------

def test_review_coverage(scalar):
    reviewed = scalar(f"SELECT count(*) FILTER (WHERE has_review) FROM mart.fct_orders WHERE {WINDOW}")
    total = scalar(f"SELECT count(*) FROM mart.fct_orders WHERE {WINDOW}")
    assert reviewed == 97_181
    assert round(100.0 * reviewed / total, 2) == 99.26


@pytest.mark.parametrize(
    "outcome,orders,mean_score,pct_low",
    [("on time", 89_182, 4.291, 9.25), ("late", 6_378, 2.271, 62.40)],
)
def test_reviews_by_punctuality(con, outcome, orders, mean_score, pct_low):
    row = con.execute(
        "SELECT n_orders, mean_review_score, pct_1_2_star "
        f"FROM mart.kpi_reviews_by_punctuality WHERE delivery_outcome = '{outcome}'"
    ).fetchone()
    assert row[0] == orders
    assert float(row[1]) == mean_score
    assert float(row[2]) == pct_low


def test_low_score_gradient_is_monotone(con):
    """The report's strongest claim: seven buckets, rising without exception."""
    values = [
        float(row[0])
        for row in con.execute(
            "SELECT pct_1_2_star FROM mart.kpi_reviews_by_delay_bucket ORDER BY delay_bucket"
        ).fetchall()
    ]
    rising = values[:-1]  # the final bucket plateaus and dips slightly
    assert rising == sorted(rising), f"gradient no longer monotone: {values}"
    assert values[2] == 12.42, "on the promised day"
    assert values[3] == 32.14, "late 1-3 days"


def test_most_low_scores_are_not_late_orders(scalar):
    """Two thirds of 1-2 star reviews sit on punctual orders."""
    low_total = scalar(
        f"SELECT count(*) FROM mart.fct_orders WHERE {MEASURABLE} AND review_score <= 2"
    )
    low_late = scalar(
        f"SELECT count(*) FROM mart.fct_orders WHERE {MEASURABLE} AND review_score <= 2 AND is_late"
    )
    assert low_total == 12_228
    assert low_late == 3_980
    assert round(100.0 * low_late / low_total, 1) == 32.5


def test_multi_seller_orders_are_the_open_question(con):
    """Less late, much worse reviewed. The report must not explain this away."""
    rows = con.execute(
        "SELECT is_multi_seller, count(*), round(avg(review_score), 3), "
        "round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 2) "
        f"FROM mart.fct_orders WHERE {MEASURABLE} GROUP BY 1 ORDER BY 1"
    ).fetchall()
    single = next(r for r in rows if not r[0])
    multi = next(r for r in rows if r[0])
    assert (single[1], float(single[2]), float(single[3])) == (94_931, 4.173, 6.87)
    assert (multi[1], float(multi[2]), float(multi[3])) == (1_272, 2.862, 1.02)
    assert float(multi[3]) < float(single[3]), "multi-seller orders are LESS late"
    assert float(multi[2]) < float(single[2]), "and rated worse"


# --------------------------------------------------------------------------
# Q4
# --------------------------------------------------------------------------

def test_top_five_states_concentration(con):
    row = con.execute(
        "WITH ranked AS (SELECT n_orders, n_late_orders, "
        "  row_number() OVER (ORDER BY excess_late_orders DESC) AS rn "
        "  FROM mart.kpi_state_priority) "
        "SELECT sum(n_orders) FILTER (WHERE rn <= 5), sum(n_late_orders) FILTER (WHERE rn <= 5), "
        "       sum(n_orders), sum(n_late_orders) FROM ranked"
    ).fetchone()
    top_orders, top_late, all_orders, all_late = row
    assert round(100.0 * top_orders / all_orders, 1) == 20.3
    assert round(100.0 * top_late / all_late, 1) == 36.8


def test_item_value_in_late_orders(con):
    row = con.execute(
        "SELECT sum(items_value) FILTER (WHERE is_late), "
        "round(100.0 * sum(items_value) FILTER (WHERE is_late) / sum(items_value), 2) "
        f"FROM mart.fct_orders WHERE {MEASURABLE}"
    ).fetchone()
    assert Decimal(str(row[0])) == Decimal("985618.47")
    assert float(row[1]) == 7.48


# ---------------------------------------------------------------------------
# Uncertainty (M6)
# ---------------------------------------------------------------------------

def test_state_verdicts_against_the_national_rate(con):
    rows = dict(
        con.execute(
            "SELECT verdict, count(*) FROM mart.kpi_state_late_rate_ci GROUP BY 1"
        ).fetchall()
    )
    assert rows["worse than national"] == 15
    assert rows["not distinguishable"] == 6
    assert rows["better than national"] == 6


def test_rr_is_the_cautionary_case(con):
    """Seventh-worst point estimate, interval 20 points wide, 40 orders."""
    row = con.execute(
        "SELECT n_orders, late_rate_pct, ci_lower_pct, ci_upper_pct, ci_width_pp, verdict "
        "FROM mart.kpi_state_late_rate_ci WHERE customer_state = 'RR'"
    ).fetchone()
    assert row[0] == 40
    assert float(row[1]) == 12.50
    assert float(row[2]) == 5.46
    assert float(row[3]) == 26.11
    assert float(row[4]) == 20.65
    assert row[5] == "not distinguishable"


def test_rj_interval_is_narrow_because_the_group_is_large(con):
    row = con.execute(
        "SELECT n_orders, ci_width_pp, verdict FROM mart.kpi_state_late_rate_ci "
        "WHERE customer_state = 'RJ'"
    ).fetchone()
    assert row[0] == 12_310
    assert float(row[1]) == 1.15
    assert row[2] == "worse than national"


def test_audio_is_a_real_difference_after_all(con):
    """An earlier draft dismissed this as small-sample noise. The interval disagrees."""
    row = con.execute(
        "SELECT n_orders, n_late_orders, late_rate_pct, ci_lower_pct, ci_upper_pct, verdict "
        "FROM mart.kpi_category_late_rate_ci WHERE category = 'audio'"
    ).fetchone()
    assert (row[0], row[1]) == (346, 41)
    assert float(row[2]) == 11.85
    assert float(row[3]) == 8.86
    assert float(row[4]) == 15.68
    assert row[5] == "worse than national"


def test_largest_category_gap_at_volume_is_not_distinguishable(con):
    """office_furniture has the biggest gap above 1,000 orders and still fails."""
    row = con.execute(
        "SELECT c.rate_gap_pp, ci.verdict "
        "FROM mart.kpi_category_priority c "
        "JOIN mart.kpi_category_late_rate_ci ci USING (category) "
        "WHERE c.category = 'office_furniture'"
    ).fetchone()
    assert float(row[0]) == 1.30
    assert row[1] == "not distinguishable"


def test_category_verdict_counts(con):
    rows = dict(
        con.execute(
            "SELECT verdict, count(*) FROM mart.kpi_category_late_rate_ci GROUP BY 1"
        ).fetchall()
    )
    assert rows["worse than national"] == 5
    assert rows["not distinguishable"] == 39
    assert rows["better than national"] == 8


# ---------------------------------------------------------------------------
# Retention (M6)
# ---------------------------------------------------------------------------

def test_almost_every_customer_buys_once(con):
    row = con.execute(
        "SELECT n_customers, pct_of_customers, pct_of_orders, pct_of_items_value "
        "FROM mart.kpi_customer_orders WHERE orders_per_customer = 1"
    ).fetchone()
    assert row[0] == 92_102
    assert float(row[1]) == 96.960
    assert float(row[2]) == 93.78
    assert float(row[3]) == 94.44


def test_pooled_90_day_repeat_rate(con):
    row = con.execute(
        "SELECT sum(n_new_customers), sum(n_repeated_within_90d) "
        "FROM mart.kpi_cohort_retention_90d WHERE is_complete"
    ).fetchone()
    assert row[0] == 76_845
    assert row[1] == 1_560
    assert round(100.0 * row[1] / row[0], 2) == 2.03


def test_censored_cohorts_are_flagged_not_dropped(con):
    censored = con.execute(
        "SELECT cohort_month, repeat_rate_90d_pct FROM mart.kpi_cohort_retention_90d "
        "WHERE NOT is_complete ORDER BY cohort_month"
    ).fetchall()
    months = [str(row[0]) for row in censored]
    assert months == ["2018-06-01", "2018-07-01", "2018-08-01"], (
        "the censored set changed; the dataset ends 2018-09-03 and the 90-day "
        "window is what determines this boundary"
    )
    # Their rates look like collapse and are not: this is the artefact the
    # is_complete flag exists to prevent anyone quoting.
    assert all(float(row[1]) < 2.03 for row in censored)


def test_customer_unique_id_is_what_retention_counts(con):
    """Using customer_id would inflate the customer base by the repeat rate."""
    people = con.execute(
        "SELECT sum(n_customers) FROM mart.kpi_customer_orders"
    ).fetchone()[0]
    order_level_ids = con.execute(
        "SELECT count(DISTINCT customer_id) FROM mart.fct_orders WHERE is_sale_eligible"
    ).fetchone()[0]
    assert people < order_level_ids
