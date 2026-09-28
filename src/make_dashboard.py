"""Build the interactive dashboard from the exported aggregates.

Two files, same content:
    dashboard/olist_dashboard.html   plotly inlined, opens from disk offline
    docs/index.html                  plotly from CDN, ~200 KB, for GitHub Pages

Everything is read from dashboard/exports/, so the dashboard, the report figures
and the Power BI file all show the same numbers.

The page has four sections, a KPI row, a state filter that cross-filters the
logistics section, a table view behind every chart, and a light/dark toggle.
Figures are emitted as plotly JSON rather than rendered HTML so the theme switch
can restyle them in place: each trace carries a colour *role* in `meta`, and the
browser maps roles to hex values for the active theme.

Usage:
    python src/make_dashboard.py            # both files
    python src/make_dashboard.py --pages    # docs/index.html only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import EXPORT_DIR, PROJECT_ROOT  # noqa: E402

# Colour roles. Both modes validated for the surfaces they render on:
# light worst adjacent CVD dE 24.7 / normal 33.6; dark 26.8 / 31.8.
ROLES = {
    "series1": {"light": "#2a78d6", "dark": "#3987e5"},
    "series2": {"light": "#eb6834", "dark": "#d95926"},
    "critical": {"light": "#d03b3b", "dark": "#d03b3b"},
    "muted": {"light": "#898781", "dark": "#898781"},
}


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(EXPORT_DIR / name)


def fig_json(fig: go.Figure) -> dict:
    """Plotly JSON with the theme-dependent chrome left out."""
    # Don't clobber showlegend where a figure has already asked for one.
    wants_legend = bool(fig.layout.showlegend)
    fig.update_layout(
        margin=dict(l=62, r=24, t=14, b=76 if wants_legend else 48),
        showlegend=wants_legend,
        # Height fixed, width left to autosize: pinning the width makes plotly
        # ignore the card and draw a 700px chart whatever the container is.
        height=fig.layout.height or 380,
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=12.5),
        hoverlabel=dict(font_size=12.5),
    )
    return json.loads(fig.to_json())


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def build_figures() -> tuple[dict, dict, dict]:
    """Return (figures, tables, notes) keyed by chart id."""
    figs: dict[str, dict] = {}
    tables: dict[str, dict] = {}
    notes: dict[str, str] = {}

    sales = load("sales_monthly.csv")
    late_m = load("late_rate_monthly.csv")
    states = load("state_priority.csv")
    states_ci = load("state_late_rate_ci.csv")
    cat_ci = load("category_late_rate_ci.csv")
    cat_prio = load("category_priority.csv")
    dist = load("delay_distribution.csv")
    punct = load("reviews_by_punctuality.csv")
    buckets = load("reviews_by_delay_bucket.csv")
    coverage = load("review_coverage_monthly.csv")
    cohort = load("cohort_retention_90d.csv")
    per_customer = load("customer_orders.csv")
    payments = load("payment_mix_monthly.csv")

    def register(key: str, fig: go.Figure, df: pd.DataFrame, note: str) -> None:
        figs[key] = fig_json(fig)
        tables[key] = {"columns": list(df.columns),
                       "rows": df.astype(object).where(pd.notna(df), None).values.tolist()}
        notes[key] = note

    # --- Overview ---------------------------------------------------------
    fig = go.Figure(go.Scatter(
        x=sales["purchase_month"], y=sales["items_value"], mode="lines+markers",
        line=dict(width=2.5), marker=dict(size=7), meta=dict(role="series1"),
        customdata=sales[["n_orders", "n_customers"]],
        hovertemplate="%{x|%b %Y}<br>Item value <b>%{y:,.0f}</b> BRL"
                      "<br>%{customdata[0]:,} orders · %{customdata[1]:,} customers<extra></extra>"))
    fig.update_yaxes(title="BRL", rangemode="tozero")
    register("items-value", fig,
             sales[["purchase_month", "n_orders", "items_value", "freight_value", "aov"]],
             "Merchandise only, shipping excluded. Cancelled and unavailable orders removed. "
             "Not revenue and not profit: this dataset has no cost, tax, refund or commission data.")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sales["purchase_month"], y=sales["aov"], mode="lines", name="Average order value",
        line=dict(width=2.5), meta=dict(role="series1"),
        hovertemplate="%{x|%b %Y}<br>Order: <b>%{y:,.2f}</b> BRL<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=sales["purchase_month"], y=sales["avg_item_price"], mode="lines", name="Average item price",
        line=dict(width=2.5, dash="dash"), meta=dict(role="series2"),
        hovertemplate="%{x|%b %Y}<br>Item: <b>%{y:,.2f}</b> BRL<extra></extra>"))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.22, x=0))
    fig.update_yaxes(title="BRL", rangemode="tozero")
    register("aov", fig, sales[["purchase_month", "aov", "avg_item_price", "freight_pct_of_items"]],
             "Both series are in BRL on one axis. Volume grew about eightfold over the same "
             "period, so orders became more numerous and slightly smaller.")

    mix = payments.pivot_table(index="purchase_month", columns="dominant_payment_type",
                               values="n_orders", aggfunc="sum").fillna(0)
    ordered = mix.sum().sort_values(ascending=False).index.tolist()
    fig = go.Figure()
    for i, payment_type in enumerate(ordered[:2]):
        fig.add_trace(go.Bar(
            x=mix.index, y=mix[payment_type], name=payment_type.replace("_", " "),
            meta=dict(role="series1" if i == 0 else "series2"),
            hovertemplate="%{x|%b %Y}<br>" + payment_type.replace("_", " ")
                          + ": <b>%{y:,.0f}</b> orders<extra></extra>"))
    if len(ordered) > 2:
        fig.add_trace(go.Bar(
            x=mix.index, y=mix[ordered[2:]].sum(axis=1), name="other methods",
            meta=dict(role="muted"),
            hovertemplate="%{x|%b %Y}<br>other: <b>%{y:,.0f}</b> orders<extra></extra>"))
    fig.update_layout(barmode="stack", showlegend=True,
                      legend=dict(orientation="h", y=-0.22, x=0), bargap=0.18)
    fig.update_yaxes(title="Orders")
    register("payment-mix", fig, payments,
             "Dominant instrument per order: the method carrying the largest share of the "
             "payment. Methods beyond the top two are grouped rather than given their own hue.")

    # --- Logistics --------------------------------------------------------
    spikes = {"2017-11", "2018-02", "2018-03"}
    is_spike = late_m["purchase_month"].str.slice(0, 7).isin(spikes)
    fig = go.Figure(go.Bar(
        x=late_m["purchase_month"], y=late_m["late_rate_pct"],
        meta=dict(role="perPoint",
                  roles=["critical" if s else "series1" for s in is_spike]),
        customdata=late_m[["n_orders", "n_late_orders", "median_delay_days"]],
        hovertemplate="%{x|%b %Y}<br>Late rate <b>%{y:.2f}%</b>"
                      "<br>%{customdata[1]:,} late of %{customdata[0]:,}"
                      "<br>Median delay %{customdata[2]:.0f} days<extra></extra>"))
    fig.update_yaxes(title="Late rate", ticksuffix="%")
    register("late-monthly", fig, late_m,
             "Three months carry 48.4% of every late order. Order volume correlates with the "
             "monthly rate at r = 0.51, so volume is associated with the spikes but does not "
             "account for them: 2018-01 carried comparable volume at 5.70%.")

    ci = states_ci.sort_values("late_rate_pct")
    verdict_role = {"worse than national": "critical",
                    "better than national": "series1",
                    "not distinguishable": "muted"}
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ci["late_rate_pct"], y=ci["customer_state"], mode="markers",
        marker=dict(size=9),
        error_x=dict(type="data", symmetric=False,
                     array=(ci["ci_upper_pct"] - ci["late_rate_pct"]).tolist(),
                     arrayminus=(ci["late_rate_pct"] - ci["ci_lower_pct"]).tolist(),
                     thickness=2.2, width=0),
        meta=dict(role="perPoint", roles=[verdict_role[v] for v in ci["verdict"]],
                  errorRole="muted"),
        customdata=ci[["n_orders", "n_late_orders", "ci_lower_pct", "ci_upper_pct", "verdict"]],
        hovertemplate="<b>%{y}</b> · %{customdata[4]}<br>Late rate <b>%{x:.2f}%</b>"
                      "<br>95%% interval %{customdata[2]:.2f}%% to %{customdata[3]:.2f}%%"
                      "<br>%{customdata[1]:,} late of %{customdata[0]:,}<extra></extra>"))
    fig.update_layout(height=660)
    fig.update_xaxes(title="Late rate with 95% Wilson interval", ticksuffix="%")
    register("state-ci", fig, states_ci,
             "Wilson score interval, 95%. Red is distinguishably worse than the national rate, "
             "blue distinguishably better, grey means the interval crosses it and the state "
             "cannot be told apart from national. Hover for the verdict in words. RR&rsquo;s 12.50% "
             "rests on 40 orders and spans 5.46% to 26.11%.")

    fig = go.Figure(go.Bar(
        x=dist["delay_days"], y=dist["n_orders"],
        meta=dict(role="perPoint",
                  roles=["critical" if d > 0 else "series1" for d in dist["delay_days"]]),
        hovertemplate="%{x} days<br><b>%{y:,}</b> orders<extra></extra>"))
    fig.update_xaxes(title="Days from the promised date (negative = early)")
    fig.update_yaxes(title="Orders")
    register("delay-distribution", fig, dist,
             "Trimmed to plus or minus 40 days for readability. The median order arrives 12 days "
             "early; p99 is 18 days late and the maximum is 188.")

    fig = go.Figure(go.Scatter(
        x=cat_ci["n_orders"], y=cat_ci["late_rate_pct"], mode="markers",
        marker=dict(size=10, opacity=0.75),
        meta=dict(role="perPoint", roles=[verdict_role[v] for v in cat_ci["verdict"]]),
        text=cat_ci["category"],
        customdata=cat_ci[["n_late_orders", "ci_lower_pct", "ci_upper_pct", "verdict"]],
        hovertemplate="<b>%{text}</b> · %{customdata[3]}<br>Late rate <b>%{y:.2f}%</b>"
                      "<br>95%% interval %{customdata[1]:.2f}%% to %{customdata[2]:.2f}%%"
                      "<br>%{customdata[0]:,} late of %{x:,}<extra></extra>"))
    fig.update_xaxes(title="Orders containing the category (log scale)", type="log")
    fig.update_yaxes(title="Late rate", ticksuffix="%")
    register("category-ci", fig, cat_ci,
             "Same colour key as the state chart, and the verdict is in every hover. 39 of 52 "
             "categories cannot be distinguished from the national rate. An order counts once per "
             "category it contains, so these counts sum to more than the order total. Categories "
             "under 100 orders are excluded.")

    trend = load("late_rate_state_monthly.csv")
    fig = go.Figure(go.Scatter(
        x=[], y=[], mode="lines+markers", line=dict(width=2.5), marker=dict(size=6),
        meta=dict(role="series1"),
        hovertemplate="%{x|%b %Y}<br>Late rate <b>%{y:.2f}%</b>"
                      "<br>%{customdata[1]:,} late of %{customdata[0]:,}<extra></extra>"))
    fig.update_yaxes(title="Late rate", ticksuffix="%", rangemode="tozero")
    register("state-trend", fig, trend,
             "Monthly late rate for the state selected above. Months with fewer than 30 orders "
             "in a state are omitted, which is why small states have short lines.")

    # --- Reviews ----------------------------------------------------------
    labels = [b.split(". ", 1)[1]
               .replace("early by ", "early by<br>")
               .replace("late ", "late<br>")
               .replace("on the promised day", "on the<br>promised day")
              for b in buckets["delay_bucket"]]
    fig = go.Figure(go.Bar(
        x=labels, y=buckets["pct_1_2_star"],
        meta=dict(role="perPoint",
                  roles=["critical" if "late" in b else "series1" for b in labels]),
        customdata=buckets[["n_orders", "mean_review_score", "pct_with_comment"]],
        hovertemplate="<b>%{x}</b><br>1-2 star <b>%{y:.2f}%%</b>"
                      "<br>%{customdata[0]:,} orders · mean score %{customdata[1]:.2f}"
                      "<br>%{customdata[2]:.1f}%% left a comment<extra></extra>"))
    fig.update_yaxes(title="Share rated 1 or 2 stars", ticksuffix="%")
    register("reviews-buckets", fig, buckets,
             "Association, not causation: a hard route, a slow seller or a stock problem can "
             "produce both the delay and the low score. The break is at the promise, not at an "
             "absolute speed, and the curve plateaus past eight days.")

    fig = go.Figure(go.Bar(
        x=punct["delivery_outcome"], y=punct["mean_review_score"],
        meta=dict(role="perPoint",
                  roles=["critical" if o == "late" else "series1"
                         for o in punct["delivery_outcome"]]),
        customdata=punct[["n_orders", "pct_1_2_star", "pct_5_star"]],
        hovertemplate="<b>%{x}</b><br>Mean score <b>%{y:.3f}</b>"
                      "<br>%{customdata[0]:,} orders"
                      "<br>%{customdata[1]:.2f}%% rated 1-2 · %{customdata[2]:.2f}%% rated 5"
                      "<extra></extra>"))
    fig.update_layout(bargap=0.55)
    fig.update_yaxes(title="Mean review score", range=[0, 5])
    register("reviews-split", fig, punct,
             "One review per order, the most recent where an order carried more than one. "
             "547 orders were collapsed this way and 202 of them had disagreeing scores.")

    fig = go.Figure(go.Scatter(
        x=coverage["purchase_month"], y=coverage["review_coverage_pct"], mode="lines+markers",
        line=dict(width=2.5), marker=dict(size=6), meta=dict(role="series1"),
        customdata=coverage[["n_sale_eligible_orders", "n_reviewed", "mean_review_score"]],
        hovertemplate="%{x|%b %Y}<br>Coverage <b>%{y:.2f}%%</b>"
                      "<br>%{customdata[1]:,} reviewed of %{customdata[0]:,}"
                      "<br>Mean score %{customdata[2]:.3f}<extra></extra>"))
    fig.update_yaxes(title="Orders with a review", ticksuffix="%", range=[90, 101])
    register("review-coverage", fig, coverage,
             "Coverage is 99.26% across the window, so these scores describe nearly the whole "
             "customer base rather than a self-selected minority.")

    # --- Customers --------------------------------------------------------
    sized = cohort[cohort["n_new_customers"] >= 100].copy()
    complete = sized[sized["is_complete"]]
    censored = sized[~sized["is_complete"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=complete["cohort_month"].tolist() + complete["cohort_month"].tolist()[::-1],
        y=complete["ci_upper_pct"].tolist() + complete["ci_lower_pct"].tolist()[::-1],
        fill="toself", mode="lines", line=dict(width=0), opacity=0.16,
        meta=dict(role="series1", fillRole=True), hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=complete["cohort_month"], y=complete["repeat_rate_90d_pct"], mode="lines+markers",
        line=dict(width=2.5), marker=dict(size=6), meta=dict(role="series1"),
        customdata=complete[["n_new_customers", "n_repeated_within_90d",
                             "ci_lower_pct", "ci_upper_pct"]],
        hovertemplate="%{x|%b %Y}<br>Repeat rate <b>%{y:.2f}%%</b>"
                      "<br>%{customdata[1]:,} of %{customdata[0]:,} new customers"
                      "<br>95%% interval %{customdata[2]:.2f}%% to %{customdata[3]:.2f}%%"
                      "<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=censored["cohort_month"], y=censored["repeat_rate_90d_pct"], mode="lines+markers",
        line=dict(width=2.5, dash="dash"), marker=dict(size=6), meta=dict(role="muted"),
        customdata=censored[["n_new_customers", "n_repeated_within_90d"]],
        hovertemplate="%{x|%b %Y} · censored<br>Partial rate %{y:.2f}%%"
                      "<br>%{customdata[1]:,} of %{customdata[0]:,}"
                      "<br>Fewer than 90 days observed<extra></extra>"))
    fig.update_yaxes(title="Ordering again within 90 days", ticksuffix="%", rangemode="tozero")
    register("cohort-retention", fig, cohort,
             "Counted per customer_unique_id, the person. The dashed cohorts have not lived a "
             "full 90 days: the dataset ends 2018-09-03, so their low rates are censoring rather "
             "than collapse. Cohorts under 100 customers are omitted from the chart.")

    grouped = per_customer.copy()
    grouped["bucket"] = grouped["orders_per_customer"].apply(
        lambda n: str(int(n)) if n <= 3 else "4+")
    agg = grouped.groupby("bucket", as_index=False).agg(
        n_customers=("n_customers", "sum"),
        pct_of_customers=("pct_of_customers", "sum"),
        pct_of_orders=("pct_of_orders", "sum"),
        pct_of_items_value=("pct_of_items_value", "sum"))
    agg = agg.sort_values("bucket")
    fig = go.Figure(go.Bar(
        x=agg["bucket"], y=agg["pct_of_customers"], meta=dict(role="series1"),
        customdata=agg[["n_customers", "pct_of_orders", "pct_of_items_value"]],
        hovertemplate="<b>%{x} order(s)</b><br><b>%{y:.2f}%%</b> of customers"
                      "<br>%{customdata[0]:,} people"
                      "<br>%{customdata[1]:.2f}%% of orders · %{customdata[2]:.2f}%% of item value"
                      "<extra></extra>"))
    fig.update_layout(bargap=0.34)
    fig.update_xaxes(title="Orders placed by the same person")
    fig.update_yaxes(title="Share of customers", ticksuffix="%")
    register("orders-per-customer", fig, per_customer,
             "96.96% of customers placed exactly one order. There are 99,441 customer_id values "
             "but 96,096 people behind them, which is why customer counts use customer_unique_id.")

    # Same buckets, three shares side by side: the point is that they barely
    # differ, so repeat buyers are not carrying a disproportionate share.
    fig = go.Figure()
    for i, (col, label) in enumerate([("pct_of_customers", "customers"),
                                      ("pct_of_orders", "orders"),
                                      ("pct_of_items_value", "item value")]):
        fig.add_trace(go.Bar(
            x=agg["bucket"], y=agg[col], name=label,
            meta=dict(role=["series1", "series2", "muted"][i]),
            hovertemplate="<b>%{x} order(s)</b><br>" + label
                          + ": <b>%{y:.2f}%%</b><extra></extra>"))
    fig.update_layout(barmode="group", showlegend=True, bargap=0.28,
                      legend=dict(orientation="h", y=-0.24, x=0))
    fig.update_xaxes(title="Orders placed by the same person")
    fig.update_yaxes(title="Share of the total", ticksuffix="%")
    register("value-concentration", fig, agg,
             "One-time buyers are 96.96% of customers, 93.78% of orders and 94.44% of item "
             "value. The three shares track each other, so repeat buyers are not worth "
             "disproportionately more per head - there are simply very few of them.")

    return figs, tables, notes


# ---------------------------------------------------------------------------
# KPI tiles and page assembly
# ---------------------------------------------------------------------------

def build_tiles() -> list[dict]:
    sales = load("sales_monthly.csv")
    late_m = load("late_rate_monthly.csv")
    coverage = load("review_coverage_monthly.csv")
    cohort = load("cohort_retention_90d.csv")
    punct = load("reviews_by_punctuality.csv")

    measurable = int(late_m["n_orders"].sum())
    late = int(late_m["n_late_orders"].sum())
    reviewed = int(coverage["n_reviewed"].sum())
    eligible = int(coverage["n_sale_eligible_orders"].sum())
    done = cohort[cohort["is_complete"]]
    repeat_n = int(done["n_repeated_within_90d"].sum())
    repeat_base = int(done["n_new_customers"].sum())
    weighted_score = (punct["mean_review_score"] * punct["n_orders"]).sum() / punct["n_orders"].sum()

    return [
        {"label": "Item value",
         "value": f"{sales['items_value'].sum()/1e6:,.2f}M",
         "unit": "BRL",
         "note": f"Merchandise only, shipping excluded. {int(sales['n_orders'].sum()):,} "
                 "sale-eligible orders, 2017-01 to 2018-08. Not revenue and not profit."},
        {"label": "Late rate",
         "value": f"{100*late/measurable:.2f}%",
         "unit": f"{late:,} orders",
         "note": f"Denominator: {measurable:,} delivered orders holding both a delivery date "
                 "and an estimate. Eight orders marked delivered with no timestamp are excluded."},
        {"label": "Median delay",
         "value": "−12",
         "unit": "days (early)",
         "note": "The typical order arrives twelve days before the promised date. p90 is still "
                 "two days early; p99 is 18 days late. Lateness is a tail, not a tendency."},
        {"label": "Mean review score",
         "value": f"{weighted_score:.2f}",
         "unit": "of 5",
         "note": f"One review per order, {reviewed:,} reviewed orders. Coverage is "
                 f"{100*reviewed/eligible:.2f}% of sale-eligible orders."},
        {"label": "90-day repeat rate",
         "value": f"{100*repeat_n/repeat_base:.2f}%",
         "unit": f"{repeat_n:,} of {repeat_base:,}",
         "note": "Share of new customers placing a second order within 90 days, pooled across "
                 "cohorts that have lived a full 90 days. Counted per person."},
    ]


# (chart id, heading, span). Spans per section sum to whole rows, so no card is
# ever left alone beside dead space.
SECTIONS = [
    ("overview", "Overview", "How much was sold, and how the basket changed.",
     [("items-value", "Merchandise value by month", "half"),
      ("aov", "Average order value against average item price", "half"),
      ("payment-mix", "Payment mix by month", "full")]),
    ("logistics", "Logistics", "Where and when deliveries missed the promised date.",
     [("late-monthly", "Late rate by month", "full"),
      ("state-ci", "Late rate by destination state, with 95% intervals", "full"),
      ("state-trend", "Selected state over time", "half"),
      ("delay-distribution", "How early or late deliveries actually are", "half"),
      ("category-ci", "Late rate by category, with 95% intervals", "full")]),
    ("reviews", "Reviews", "How satisfaction relates to delivery timing.",
     [("reviews-buckets", "Low scores by how late the order was", "full"),
      ("reviews-split", "Mean score, on time against late", "half"),
      ("review-coverage", "Review coverage by month", "half")]),
    ("customers", "Customers",
     "Repeat purchasing — an extension beyond the original four questions.",
     [("cohort-retention", "90-day repeat rate by cohort", "full"),
      ("orders-per-customer", "Orders placed per person", "half"),
      ("value-concentration", "Where the orders and the value sit", "half")]),
]

# One height per span, so two charts side by side are always the same size and
# a full-width chart is always the same taller size. state-ci sets its own.
HEIGHTS = {"half": 330, "full": 390}


def render_page(plotly_js: str) -> str:
    figs, tables, notes = build_figures()
    for _, _, _, charts in SECTIONS:
        for chart_id, _, span in charts:
            layout = figs[chart_id]["layout"]
            # Same height for every chart of a span, legend or not: adding room
            # for a legend would push one card's plot below its neighbour's.
            # The legend lives in the bottom margin instead.
            if chart_id != "state-ci":
                layout["height"] = HEIGHTS[span]
    tiles = build_tiles()
    states = sorted(load("state_priority.csv")["customer_state"].tolist())
    trend = load("late_rate_state_monthly.csv")
    trend_payload = {
        state: {
            "x": group["purchase_month"].tolist(),
            "y": group["late_rate_pct"].tolist(),
            "customdata": group[["n_orders", "n_late_orders"]].values.tolist(),
        }
        for state, group in trend.groupby("customer_state")
    }
    state_facts = {
        row["customer_state"]: {
            "rate": row["late_rate_pct"], "n": int(row["n_orders"]),
            "late": int(row["n_late_orders"]), "lo": row["ci_lower_pct"],
            "hi": row["ci_upper_pct"], "verdict": row["verdict"],
        }
        for _, row in load("state_late_rate_ci.csv").iterrows()
    }

    nav = "".join(
        f'<button class="tab" data-section="{key}" role="tab" aria-selected="false">{title}</button>'
        for key, title, _, _ in SECTIONS)

    tile_html = "".join(
        f'<div class="tile"><div class="tile-label">{t["label"]}</div>'
        f'<div class="tile-value">{t["value"]}</div>'
        f'<div class="tile-unit">{t["unit"]}</div>'
        f'<p class="tile-note">{t["note"]}</p></div>'
        for t in tiles)

    def card(chart_id: str, heading: str, span: str) -> str:
        wide = " wide" if span == "full" else ""
        return f"""
        <figure class="card{wide}" id="card-{chart_id}">
          <figcaption>
            <h3>{heading}</h3>
            <button class="toggle" data-chart="{chart_id}" aria-pressed="false">Table</button>
          </figcaption>
          <p class="note">{notes[chart_id]}</p>
          <div class="plot" id="plot-{chart_id}"></div>
          <div class="table-wrap" id="table-{chart_id}" hidden></div>
        </figure>"""

    sections_html = ""
    for key, title, blurb, charts in SECTIONS:
        filter_html = ""
        if key == "logistics":
            options = "".join(f'<option value="{s}">{s}</option>' for s in states)
            filter_html = f"""
          <div class="filters">
            <label for="state-filter">Focus on a state</label>
            <select id="state-filter">{options}</select>
            <span id="state-readout" class="readout"></span>
          </div>"""
        sections_html += f"""
        <section class="panel" id="section-{key}" hidden>
          <p class="blurb">{blurb}</p>{filter_html}
          <div class="grid">{"".join(card(cid, head, span) for cid, head, span in charts)}</div>
        </section>"""

    payload = json.dumps({
        "figures": figs, "tables": tables, "roles": ROLES,
        "trend": trend_payload, "stateFacts": state_facts,
    }, separators=(",", ":"), allow_nan=False)

    return f"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Olist — delivery performance and satisfaction</title>
{plotly_js}
<style>
:root {{
  color-scheme: light;
  --plane: #f9f9f7;
  --surface: #fcfcfb;
  --ink: #0b0b0b;
  --ink-2: #52514e;
  --muted: #898781;
  --grid: #e1e0d9;
  --axis: #c3c2b7;
  --border: rgba(11,11,11,0.10);
  --accent: #2a78d6;
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --plane: #0d0d0d;
  --surface: #1a1a19;
  --ink: #ffffff;
  --ink-2: #c3c2b7;
  --muted: #898781;
  --grid: #2c2c2a;
  --axis: #383835;
  --border: rgba(255,255,255,0.10);
  --accent: #3987e5;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--plane); color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 15px; line-height: 1.5;
}}
.shell {{ max-width: 1180px; margin: 0 auto; padding: 28px 18px 72px; }}
header.top {{ display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }}
header.top h1 {{ font-size: 25px; margin: 0 0 6px; letter-spacing: -0.01em; }}
.lede {{ color: var(--ink-2); margin: 0; max-width: 68ch; }}
.spacer {{ flex: 1 1 60px; }}
#theme {{
  background: var(--surface); color: var(--ink-2); border: 1px solid var(--border);
  border-radius: 999px; padding: 7px 15px; cursor: pointer; font: inherit; font-size: 13px;
  white-space: nowrap;
}}
#theme:hover {{ color: var(--ink); }}

.tiles {{ display: grid; gap: 12px; margin: 26px 0 8px;
  grid-template-columns: repeat(auto-fit, minmax(186px, 1fr)); }}
/* The label/value/unit block is a fixed height, so putting the note straight
   after it lands every divider on the same line across the row. Pushing the
   note to the bottom instead would align the tiles' feet and stagger the
   dividers, which is the more visible of the two. */
.tile {{ background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 15px 12px; }}
.tile-label {{ font-size: 12.5px; color: var(--ink-2); }}
.tile-value {{ font-size: 27px; font-weight: 600; letter-spacing: -0.02em;
  margin-top: 2px; line-height: 1.15; }}
.tile-unit {{ font-size: 12.5px; color: var(--muted); }}
.tile-note {{
  font-size: 12.5px; color: var(--ink-2); line-height: 1.45;
  margin: 12px 0 0; padding-top: 10px; border-top: 1px solid var(--border);
}}

nav.tabs {{ display: flex; gap: 6px; flex-wrap: wrap; margin: 26px 0 18px;
  border-bottom: 1px solid var(--border); }}
.tab {{ background: none; border: none; border-bottom: 2px solid transparent;
  padding: 9px 13px; font: inherit; font-size: 14px; color: var(--ink-2);
  cursor: pointer; margin-bottom: -1px; }}
.tab:hover {{ color: var(--ink); }}
.tab[aria-selected="true"] {{ color: var(--ink); border-bottom-color: var(--accent);
  font-weight: 600; }}

.blurb {{ color: var(--ink-2); margin: 0 0 16px; max-width: 72ch; }}
.panel {{ animation: fade 160ms ease-out; }}
@keyframes fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
.filters {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin: 0 0 18px; padding: 11px 13px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px; }}
.filters label {{ font-size: 13px; color: var(--ink-2); }}
.filters select {{ font: inherit; font-size: 14px; padding: 5px 9px; border-radius: 7px;
  border: 1px solid var(--border); background: var(--plane); color: var(--ink); }}
.readout {{ font-size: 13px; color: var(--ink-2); }}
.readout b {{ color: var(--ink); }}

.grid {{
  display: grid; gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;          /* cards in a row share a height... */
}}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px 16px 10px; margin: 0; min-width: 0;
  display: flex; flex-direction: column;   /* ...and the plot sits at the bottom */
}}
.card.wide {{ grid-column: 1 / -1; }}
figcaption {{ display: flex; align-items: baseline; gap: 12px; min-height: 26px; }}
figcaption h3 {{ font-size: 15.5px; margin: 0; flex: 1; line-height: 1.3; }}
.toggle {{ background: none; border: 1px solid var(--border); border-radius: 7px;
  color: var(--ink-2); font: inherit; font-size: 12px; padding: 3px 10px;
  cursor: pointer; flex: none; }}
.toggle:hover {{ color: var(--ink); }}
.toggle[aria-pressed="true"] {{ color: var(--ink); border-color: var(--accent); }}
/* Notes run 2-4 lines. Reserving three keeps the plot baselines level across a
   row without truncating the longer ones. */
.note {{ font-size: 12.5px; color: var(--ink-2); margin: 8px 0 10px;
  line-height: 1.45; min-height: 3em; }}
.plot {{ width: 100%; margin-top: auto; }}
.table-wrap {{ overflow-x: auto; max-height: 430px; overflow-y: auto; margin-bottom: 10px; }}
table {{ border-collapse: collapse; font-size: 12.5px; width: 100%; }}
th, td {{ text-align: right; padding: 5px 9px; border-bottom: 1px solid var(--border);
  white-space: nowrap; font-variant-numeric: tabular-nums; }}
th {{ position: sticky; top: 0; background: var(--surface); text-align: right;
  color: var(--ink-2); font-weight: 600; }}
th:first-child, td:first-child {{ text-align: left; font-variant-numeric: normal; }}

footer {{ margin-top: 30px; color: var(--muted); font-size: 12.5px; line-height: 1.6;
  max-width: 78ch; }}
footer a {{ color: inherit; }}

@media (max-width: 860px) {{
  .grid {{ grid-template-columns: 1fr; }}
  .card.wide {{ grid-column: auto; }}
  .note {{ min-height: 0; }}
  .tiles {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
  .shell {{ padding: 20px 14px 56px; }}
}}
</style>
</head>
<body>
<div class="shell">

<header class="top">
  <div>
    <h1>Olist — delivery performance and satisfaction</h1>
    <p class="lede">Brazilian marketplace, 2017-01 to 2018-08. Every figure comes from
    <code>dashboard/exports/</code>, which is reconciled against the DuckDB model at export
    time. Group sizes are on every hover, because a rate without its denominator is not
    quotable.</p>
  </div>
  <div class="spacer"></div>
  <button id="theme" aria-label="Switch colour theme">Dark</button>
</header>

<div class="tiles">{tile_html}</div>

<nav class="tabs" role="tablist">{nav}</nav>
{sections_html}

<footer>
  Item value, shipping and payments are three different measures and none of them is profit:
  this dataset contains no cost, tax, refund or commission data.<br>
  Relationships shown are associations, not causal effects. Confidence intervals describe
  sampling variability only.<br>
  Data: Olist Brazilian E-Commerce, CC BY-NC-SA 4.0. Only aggregates are published here.
  Generated {date.today().isoformat()}.
</footer>

</div>
<script id="payload" type="application/json">{payload}</script>
<script>
(function () {{
  const DATA = JSON.parse(document.getElementById("payload").textContent);
  const root = document.documentElement;
  const drawn = new Set();

  // en-US throughout: the browser locale disagreed with plotly's comma
  // separators, so 12,310 was rendering as 12.310 next to a chart saying 12,310.
  const num = (v) => Number(v).toLocaleString("en-US");
  const theme = () => root.getAttribute("data-theme");
  const hex = (role) => (DATA.roles[role] || DATA.roles.muted)[theme()];
  const css = (name) => getComputedStyle(root).getPropertyValue(name).trim();

  // Plotly.react takes a nested layout object; dotted paths only work in
  // relayout, so these have to be real nested keys or they are silently ignored.
  function chrome(base) {{
    const axis = {{
      gridcolor: css("--grid"),
      gridwidth: 1,
      linecolor: css("--axis"),
      zeroline: false,
      tickfont: {{ color: css("--muted"), size: 11.5 }},
      title: {{ font: {{ color: css("--ink-2"), size: 12 }} }},
      automargin: true
    }};
    const layout = Object.assign({{}}, base, {{
      paper_bgcolor: css("--surface"),
      plot_bgcolor: css("--surface"),
      font: Object.assign({{}}, base.font, {{ color: css("--ink-2") }}),
      hoverlabel: {{
        bgcolor: css("--surface"),
        bordercolor: css("--axis"),
        font: {{ color: css("--ink"), size: 12.5 }}
      }},
      legend: Object.assign({{}}, base.legend, {{ font: {{ color: css("--ink-2") }} }})
    }});
    ["xaxis", "yaxis"].forEach((key) => {{
      layout[key] = Object.assign({{}}, axis, base[key], {{
        gridcolor: axis.gridcolor,
        linecolor: axis.linecolor,
        zeroline: false,
        tickfont: axis.tickfont,
        title: Object.assign({{}}, axis.title,
          typeof (base[key] || {{}}).title === "string"
            ? {{ text: base[key].title }} : (base[key] || {{}}).title)
      }});
    }});
    return layout;
  }}

  // Colour is applied here rather than baked into the figure, so a theme switch
  // restyles in place instead of rebuilding.
  function paint(trace) {{
    const meta = trace.meta || {{}};
    if (meta.role === "perPoint") {{
      const colors = (meta.roles || []).map(hex);
      if (trace.type === "bar") {{
        trace.marker = Object.assign({{}}, trace.marker, {{ color: colors }});
      }} else {{
        trace.marker = Object.assign({{}}, trace.marker, {{
          color: colors,
          line: {{ color: css("--surface"), width: 1.2 }}
        }});
        // error_x.color takes a single value, never an array: the verdict colour
        // rides on the marker and the interval stays recessive.
        if (trace.error_x) {{
          trace.error_x = Object.assign({{}}, trace.error_x,
            {{ color: hex(meta.errorRole || "muted") }});
        }}
      }}
    }} else if (meta.role) {{
      const c = hex(meta.role);
      if (trace.line) trace.line = Object.assign({{}}, trace.line, {{ color: c }});
      if (trace.type === "bar") {{
        trace.marker = Object.assign({{}}, trace.marker, {{ color: c }});
      }} else if (trace.mode && trace.mode.indexOf("markers") !== -1) {{
        trace.marker = Object.assign({{}}, trace.marker, {{
          color: c, line: {{ color: css("--surface"), width: 1.4 }}
        }});
      }}
      if (meta.fillRole) trace.fillcolor = c;
    }}
    return trace;
  }}

  function draw(id) {{
    const spec = DATA.figures[id];
    if (!spec) return;
    const traces = spec.data.map((t) => paint(JSON.parse(JSON.stringify(t))));
    const layout = chrome(spec.layout);
    Plotly.react("plot-" + id, traces, layout,
      {{ displayModeBar: false, responsive: true }});
    drawn.add(id);
  }}

  function retheme() {{
    drawn.forEach((id) => {{
      const el = document.getElementById("plot-" + id);
      if (el && el.offsetParent !== null) draw(id);
      else drawn.delete(id);   // redraw it when its section is next opened
    }});
  }}

  // --- tables -----------------------------------------------------------
  function renderTable(id) {{
    const t = DATA.tables[id];
    const head = "<tr>" + t.columns.map((c) => "<th>" + c + "</th>").join("") + "</tr>";
    const body = t.rows.map((r) => "<tr>" + r.map((v) =>
      "<td>" + (v === null ? "" : typeof v === "number"
        ? (Number.isInteger(v) ? num(v) : Number(v).toLocaleString("en-US",
            {{ maximumFractionDigits: 2 }}))
        : String(v)) + "</td>").join("") + "</tr>").join("");
    document.getElementById("table-" + id).innerHTML =
      "<table><thead>" + head + "</thead><tbody>" + body + "</tbody></table>";
  }}

  document.querySelectorAll(".toggle").forEach((btn) => {{
    btn.addEventListener("click", () => {{
      const id = btn.dataset.chart;
      const showing = btn.getAttribute("aria-pressed") === "true";
      const table = document.getElementById("table-" + id);
      if (!showing && !table.innerHTML) renderTable(id);
      table.hidden = showing;
      document.getElementById("plot-" + id).hidden = !showing;
      btn.setAttribute("aria-pressed", String(!showing));
      btn.textContent = showing ? "Table" : "Chart";
    }});
  }});

  // --- sections ---------------------------------------------------------
  function show(section) {{
    document.querySelectorAll(".panel").forEach((p) => {{
      p.hidden = p.id !== "section-" + section;
    }});
    document.querySelectorAll(".tab").forEach((t) => {{
      t.setAttribute("aria-selected", String(t.dataset.section === section));
    }});
    // Draw and size on the next frame: inside the click handler the panel has
    // only just been unhidden and still measures zero width.
    requestAnimationFrame(() => {{
      document.querySelectorAll("#section-" + section + " .plot").forEach((el) => {{
        const id = el.id.replace("plot-", "");
        if (!drawn.has(id)) draw(id);
        Plotly.Plots.resize(el);
      }});
    }});
  }}
  document.querySelectorAll(".tab").forEach((t) => {{
    t.addEventListener("click", () => {{
      show(t.dataset.section);
      const tabs = document.querySelector("nav.tabs");
      const y = window.scrollY + tabs.getBoundingClientRect().top - 12;
      if (window.scrollY > y) window.scrollTo({{ top: y, behavior: "smooth" }});
    }});
  }});

  // --- state filter -----------------------------------------------------
  const select = document.getElementById("state-filter");
  function applyState(state) {{
    const series = DATA.trend[state];
    const spec = DATA.figures["state-trend"];
    spec.data[0].x = series ? series.x : [];
    spec.data[0].y = series ? series.y : [];
    spec.data[0].customdata = series ? series.customdata : [];
    spec.layout.title = undefined;
    if (drawn.has("state-trend")) draw("state-trend");

    const f = DATA.stateFacts[state];
    const readout = document.getElementById("state-readout");
    if (f) {{
      readout.innerHTML = "<b>" + state + "</b>: " + f.rate.toFixed(2) +
        "% late (" + num(f.late) + " of " + num(f.n) +
        "), 95% interval " + f.lo.toFixed(2) + "% to " + f.hi.toFixed(2) +
        " — " + f.verdict + ".";
    }}
    // Dim every other state in the interval chart so the selection is findable.
    const ci = DATA.figures["state-ci"];
    const labels = ci.data[0].y;
    ci.data[0].marker = ci.data[0].marker || {{}};
    ci.data[0].marker.opacity = labels.map((s) => (s === state ? 1 : 0.32));
    if (drawn.has("state-ci")) draw("state-ci");
  }}
  if (select) {{
    select.value = "RJ";
    select.addEventListener("change", () => applyState(select.value));
    applyState("RJ");
  }}

  // --- theme ------------------------------------------------------------
  const button = document.getElementById("theme");
  function setTheme(next) {{
    root.setAttribute("data-theme", next);
    button.textContent = next === "dark" ? "Light" : "Dark";
    retheme();
  }}
  const prefersDark = window.matchMedia
    && window.matchMedia("(prefers-color-scheme: dark)").matches;
  let stored = null;
  try {{ stored = localStorage.getItem("olist-theme"); }} catch (e) {{ stored = null; }}
  setTheme(stored || (prefersDark ? "dark" : "light"));
  button.addEventListener("click", () => {{
    const next = theme() === "dark" ? "light" : "dark";
    try {{ localStorage.setItem("olist-theme", next); }} catch (e) {{}}
    setTheme(next);
  }});

  show("overview");
}})();
</script>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", action="store_true", help="only build docs/index.html")
    parser.add_argument("--local", action="store_true", help="only build the offline file")
    args = parser.parse_args()
    both = not (args.pages or args.local)

    if args.local or both:
        import plotly.offline as pyo
        inline = f"<script>{pyo.get_plotlyjs()}</script>"
        out = PROJECT_ROOT / "dashboard" / "olist_dashboard.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_page(inline), encoding="utf-8")
        print(f"  wrote {out.relative_to(PROJECT_ROOT)} "
              f"({out.stat().st_size/1_048_576:.1f} MB, opens offline)")

    if args.pages or both:
        cdn = ('<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" '
               'charset="utf-8"></script>')
        out = PROJECT_ROOT / "docs" / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_page(cdn), encoding="utf-8")
        print(f"  wrote {out.relative_to(PROJECT_ROOT)} "
              f"({out.stat().st_size/1024:,.0f} KB, plotly from CDN)")


if __name__ == "__main__":
    main()
