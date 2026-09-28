"""Render the report figures from the exported aggregates.

Charts are built from dashboard/exports/*.csv, not from fresh queries, so the
figures and the dashboard are guaranteed to show the same numbers. If a figure
and a Power BI visual ever disagree, the cause is the visual, not the data.

Two outputs, deliberately:
  reports/figures/*.png   static, for the written report
  dashboard/olist_charts.html  self-contained interactive page with hover,
                               for anyone who will not install Power BI

Design notes:
  - One y-axis per chart. Two measures of different scale get two charts.
  - Group sizes (n) are printed on the chart, never left to a footnote.
  - Colors are a validated two-slot categorical palette; nothing is encoded by
    color alone, and every multi-series chart is also directly labelled.

Usage:
    python src/make_charts.py            # both outputs
    python src/make_charts.py --png      # figures only
    python src/make_charts.py --html     # interactive page only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import EXPORT_DIR, FIGURE_DIR, PROJECT_ROOT  # noqa: E402

# --- Palette -------------------------------------------------------------
# Validated categorical slots 1 and 2 (light surface #fcfcfb): worst adjacent
# CVD dE 24.7, normal-vision dE 33.6, both >= 3:1 contrast. No chart here uses
# more than two categorical series.
SERIES_1 = "#2a78d6"   # blue
SERIES_2 = "#eb6834"   # orange
CRITICAL = "#d03b3b"   # status: critical (icon/label always accompanies it)
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": ["DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "semibold",
    "axes.titlecolor": INK,
    "axes.labelcolor": INK_SECONDARY,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 1.0,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "legend.frameon": False,
})


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(EXPORT_DIR / name)


def finish(ax, title: str, subtitle: str, source: str) -> None:
    """Common chrome: recessive grid, no top/right spines, sourced caption.

    Title and subtitle are drawn as explicit text rather than via set_title, so
    the two never land on the same baseline regardless of figure height.
    """
    ax.text(0, 1.105, title, transform=ax.transAxes, fontsize=13,
            fontweight="semibold", color=INK, va="bottom")
    ax.text(0, 1.028, subtitle, transform=ax.transAxes, fontsize=9.5,
            color=INK_SECONDARY, va="bottom")
    # Below the figure box, so it can never land on rotated tick labels.
    ax.figure.text(0.01, -0.035, source, fontsize=8, color=MUTED, va="top")
    ax.grid(axis="y", alpha=0.9)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def save(fig, name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path.relative_to(PROJECT_ROOT)}")


# --- Figures -------------------------------------------------------------

def fig_sales_monthly() -> None:
    df = load("sales_monthly.csv")
    df["purchase_month"] = pd.to_datetime(df["purchase_month"])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(df["purchase_month"], df["items_value"] / 1000,
            color=SERIES_1, linewidth=2, marker="o", markersize=4.5,
            markerfacecolor=SURFACE, markeredgewidth=1.6, markeredgecolor=SERIES_1)
    last = df.iloc[-1]
    ax.annotate(f"{last['items_value']/1000:,.0f}k",
                (last["purchase_month"], last["items_value"] / 1000),
                textcoords="offset points", xytext=(8, -2),
                color=SERIES_1, fontsize=10, fontweight="semibold")
    ax.set_ylabel("Item value, thousands BRL")
    ax.set_ylim(bottom=0)
    finish(ax, "Merchandise value grew roughly eightfold in 20 months",
           f"Item value only, shipping excluded · {df['n_orders'].sum():,} orders, "
           "cancelled and unavailable excluded",
           "Source: Olist 2017-01..2018-08, mart.kpi_sales_monthly. Not revenue or profit: "
           "no cost, tax, refund or commission data exists in this dataset.")
    save(fig, "01_sales_monthly.png")


def fig_aov_monthly() -> None:
    df = load("sales_monthly.csv")
    df["purchase_month"] = pd.to_datetime(df["purchase_month"])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    # Two series, same unit and comparable scale, so one axis is honest.
    ax.plot(df["purchase_month"], df["aov"], color=SERIES_1, linewidth=2, label="Average order value")
    ax.plot(df["purchase_month"], df["avg_item_price"], color=SERIES_2, linewidth=2,
            linestyle="--", label="Average item price")
    for series, color, label in ((df["aov"], SERIES_1, "order"), (df["avg_item_price"], SERIES_2, "item")):
        ax.annotate(f"{series.iloc[-1]:,.0f} ({label})",
                    (df["purchase_month"].iloc[-1], series.iloc[-1]),
                    textcoords="offset points", xytext=(8, -3), color=color,
                    fontsize=9.5, fontweight="semibold")
    ax.set_ylabel("BRL")
    ax.set_ylim(bottom=0)
    ax.legend(loc="lower left", fontsize=9)
    finish(ax, "Orders got more numerous and slightly cheaper",
           "Average order value fell from 152.60 to 132.20 while volume grew · "
           "n = 20 months",
           "Source: mart.kpi_sales_monthly. Association only; no pricing or promotion data "
           "is available to explain the decline.")
    save(fig, "02_aov_monthly.png")


def fig_late_rate_by_state() -> None:
    df = load("state_priority.csv").sort_values("late_rate_pct", ascending=True)
    # Computed, never hardcoded: the benchmark must share the chart's own
    # denominator. 6.79% is the rate inside the analysis window; 6.77% is the
    # rate over all measurable orders including the sparse boundary months.
    benchmark = 100.0 * df["n_late_orders"].sum() / df["n_orders"].sum()
    fig, ax = plt.subplots(figsize=(8.2, 8.4))
    colors = [CRITICAL if rate >= 12 else SERIES_1 for rate in df["late_rate_pct"]]
    bars = ax.barh(df["customer_state"], df["late_rate_pct"], color=colors, height=0.72)
    ax.axvline(benchmark, color=MUTED, linewidth=1.4, linestyle=":")
    ax.text(benchmark + 0.3, len(df) - 0.4, f"national {benchmark:.2f}%", color=MUTED, fontsize=9)
    for bar, (_, row) in zip(bars, df.iterrows()):
        ax.text(bar.get_width() + 0.35, bar.get_y() + bar.get_height() / 2,
                f"{row['late_rate_pct']:.1f}%   n={int(row['n_orders']):,}",
                va="center", fontsize=8.6, color=INK_SECONDARY)
    ax.set_xlabel("Share of delivered orders arriving after the promised date")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlim(0, df["late_rate_pct"].max() * 1.32)
    ax.grid(axis="x", alpha=0.9)
    ax.grid(axis="y", visible=False)
    finish(ax, "Late delivery is a geography problem, not a category problem",
           "Destination state · red marks states at or above 12% · "
           f"{int(df['n_orders'].sum()):,} measurable delivered orders",
           "Source: mart.kpi_state_priority. Denominator: delivered orders holding both a "
           "delivery date and an estimate. Small states carry wide uncertainty; n is shown for each.")
    ax.grid(axis="y", visible=False)
    save(fig, "03_late_rate_by_state.png")


def fig_delay_distribution() -> None:
    df = load("delay_distribution.csv")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    colors = [CRITICAL if d > 0 else SERIES_1 for d in df["delay_days"]]
    ax.bar(df["delay_days"], df["n_orders"], color=colors, width=0.86)
    ax.axvline(0, color=INK_SECONDARY, linewidth=1.4)
    ax.text(0.6, df["n_orders"].max() * 0.92, "promised date",
            color=INK_SECONDARY, fontsize=9)
    early = int(df.loc[df["delay_days"] < 0, "n_orders"].sum())
    late = int(df.loc[df["delay_days"] > 0, "n_orders"].sum())
    ax.text(-39, df["n_orders"].max() * 0.72, f"early\nn={early:,}",
            color=SERIES_1, fontsize=10, fontweight="semibold")
    ax.text(14, df["n_orders"].max() * 0.72, f"late\nn={late:,}",
            color=CRITICAL, fontsize=10, fontweight="semibold")
    ax.set_xlabel("Days between promised date and actual delivery (negative = early)")
    ax.set_ylabel("Orders")
    finish(ax, "The typical order arrives twelve days early",
           "Delivery estimates are heavily padded; lateness is a tail, not the centre · "
           "trimmed to plus or minus 40 days",
           "Source: mart.fct_orders. Orders beyond the plotted range exist and are counted in "
           "the report text, not drawn here.")
    save(fig, "04_delay_distribution.png")


def fig_reviews_by_delay() -> None:
    df = load("reviews_by_delay_bucket.csv")
    # Two short lines instead of one rotated label: rotation collides with the
    # source caption and costs the reader a head tilt for no benefit.
    labels = [
        b.split(". ", 1)[1].replace("early by ", "early\n").replace("late ", "late\n")
         .replace("on the promised day", "on the\npromised day")
        for b in df["delay_bucket"]
    ]
    fig, ax = plt.subplots(figsize=(9.4, 5.0))
    colors = [CRITICAL if "late" in label else SERIES_1 for label in labels]
    bars = ax.bar(range(len(df)), df["pct_1_2_star"], color=colors, width=0.68)
    for bar, (_, row) in zip(bars, df.iterrows()):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.6,
                f"{row['pct_1_2_star']:.1f}%", ha="center", fontsize=9.5,
                color=INK, fontweight="semibold")
        ax.text(bar.get_x() + bar.get_width() / 2, 1.8,
                f"n={int(row['n_orders']):,}", ha="center", fontsize=8.4, color=SURFACE)
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, fontsize=8.8)
    ax.set_ylabel("Share of reviewed orders rated 1 or 2 stars")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_ylim(0, 92)
    finish(ax, "Dissatisfaction rises the moment the promise is broken",
           "Low scores jump from 12.4% on the promised day to 32.1% at one to three days late · "
           f"n = {int(df['n_orders'].sum()):,} reviewed orders",
           "Source: mart.kpi_reviews_by_delay_bucket. ASSOCIATION, NOT CAUSATION: a hard route, "
           "a slow seller or a stock problem can produce both the delay and the low score.")
    save(fig, "05_reviews_by_delay_bucket.png")


def fig_category_priority() -> None:
    df = load("category_priority.csv")
    benchmark = df["benchmark_late_rate_pct"].iloc[0]
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.scatter(df["n_orders"], df["late_rate_pct"],
               s=df["items_value"] / 4000 + 18, color=SERIES_1, alpha=0.55,
               edgecolor=SURFACE, linewidth=1.4, zorder=3)
    ax.axhline(benchmark, color=MUTED, linestyle=":", linewidth=1.4)
    ax.text(df["n_orders"].min(), benchmark + 0.22,
            f"national late rate {benchmark:.2f}%", color=MUTED, fontsize=9)
    # Label only the three largest, alternating the offset: six labels in this
    # corner overlap each other and stop being readable at all.
    for rank, (_, row) in enumerate(df.nlargest(3, "n_orders").iterrows()):
        ax.annotate(row["category"], (row["n_orders"], row["late_rate_pct"]),
                    textcoords="offset points",
                    xytext=(14, (18, -16, -38)[rank]),
                    fontsize=8.8, color=INK_SECONDARY,
                    arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.8))
    outlier = df.nlargest(1, "late_rate_pct").iloc[0]
    ax.annotate(f"{outlier['category']} (n={int(outlier['n_orders'])})",
                (outlier["n_orders"], outlier["late_rate_pct"]),
                textcoords="offset points", xytext=(9, 0), fontsize=8.8, color=CRITICAL)
    ax.set_xscale("log")
    ax.set_xlim(right=df["n_orders"].max() * 2.4)
    ax.set_xlabel("Orders containing the category (log scale)")
    ax.set_ylabel("Late rate")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    finish(ax, "No category stands out once volume is taken into account",
           "Categories with 1,000+ orders span 4.32% to 8.09% late · "
           "bubble area is item value · categories under 100 orders excluded",
           "Source: mart.kpi_category_priority. An order is counted once per category it "
           "contains, so category order counts sum to more than the order total.")
    save(fig, "06_category_priority.png")


def fig_late_rate_monthly() -> None:
    df = load("late_rate_monthly.csv")
    df["purchase_month"] = pd.to_datetime(df["purchase_month"])
    spikes = {"2017-11", "2018-02", "2018-03"}
    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    colors = [CRITICAL if m.strftime("%Y-%m") in spikes else SERIES_1
              for m in df["purchase_month"]]
    bars = ax.bar(df["purchase_month"], df["late_rate_pct"], color=colors, width=22)
    baseline = 100.0 * df.loc[~df["purchase_month"].dt.strftime("%Y-%m").isin(spikes),
                              "n_late_orders"].sum() / \
               df.loc[~df["purchase_month"].dt.strftime("%Y-%m").isin(spikes), "n_orders"].sum()
    ax.axhline(baseline, color=MUTED, linestyle=":", linewidth=1.4)
    # Anchored over the low-bar stretch so the label never crosses a bar top.
    ax.text(df["purchase_month"].iloc[4], baseline + 0.6,
            f"rate in the other 17 months: {baseline:.2f}%", color=MUTED, fontsize=9)
    for bar, (_, row) in zip(bars, df.iterrows()):
        if row["purchase_month"].strftime("%Y-%m") in spikes:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{row['late_rate_pct']:.1f}%\nn={int(row['n_late_orders']):,}",
                    ha="center", fontsize=8.6, color=CRITICAL, fontweight="semibold")
    ax.set_ylabel("Late rate")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_ylim(0, df["late_rate_pct"].max() * 1.35)
    finish(ax, "Lateness is episodic, not a constant background rate",
           "Three months out of twenty carry 48.4% of every late order · "
           "n = 96,203 measurable delivered orders",
           "Source: mart.fct_orders. Order volume correlates with the monthly late rate at "
           "r = 0.51, so volume is associated with the spikes but does not account for them: "
           "2018-01 carried comparable volume at a 5.70% rate.")
    save(fig, "07_late_rate_monthly.png")


FIGURES = [
    fig_sales_monthly,
    fig_aov_monthly,
    fig_late_rate_by_state,
    fig_delay_distribution,
    fig_reviews_by_delay,
    fig_category_priority,
    fig_late_rate_monthly,
]


def build_png() -> None:
    print("Rendering figures:")
    for figure in FIGURES:
        figure()


# --- Interactive HTML ----------------------------------------------------

def build_html() -> None:
    """Self-contained page with hover, for viewers without Power BI."""
    import plotly.graph_objects as go
    import plotly.io as pio

    out = PROJECT_ROOT / "dashboard" / "olist_charts.html"
    blocks: list[str] = []
    first = True

    def add(fig: go.Figure, heading: str, note: str) -> None:
        nonlocal first
        fig.update_layout(
            template="plotly_white", font=dict(family="system-ui, sans-serif", size=13, color=INK),
            paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, margin=dict(l=60, r=30, t=10, b=50),
            hovermode="x unified", height=420, showlegend=False,
        )
        fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False)
        fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zeroline=False)
        html = pio.to_html(fig, full_html=False, include_plotlyjs="inline" if first else False,
                           config={"displayModeBar": False})
        first = False
        blocks.append(f"<section><h2>{heading}</h2><p class='note'>{note}</p>{html}</section>")

    sales = load("sales_monthly.csv")
    fig = go.Figure(go.Scatter(
        x=sales["purchase_month"], y=sales["items_value"], mode="lines+markers",
        line=dict(color=SERIES_1, width=2), marker=dict(size=7),
        hovertemplate="%{x|%b %Y}<br>Item value %{y:,.0f} BRL<extra></extra>"))
    fig.update_yaxes(title="Item value, BRL", rangemode="tozero")
    add(fig, "Merchandise value over time",
        "Item value only, shipping excluded. Cancelled and unavailable orders removed. "
        "Not revenue and not profit.")

    states = load("state_priority.csv").sort_values("late_rate_pct")
    fig = go.Figure(go.Bar(
        x=states["late_rate_pct"], y=states["customer_state"], orientation="h",
        marker_color=[CRITICAL if r >= 12 else SERIES_1 for r in states["late_rate_pct"]],
        customdata=states[["n_orders", "n_late_orders", "median_delivery_days"]],
        hovertemplate="<b>%{y}</b><br>Late rate %{x:.2f}%<br>"
                      "Orders %{customdata[0]:,}<br>Late orders %{customdata[1]:,}<br>"
                      "Median delivery %{customdata[2]:.0f} days<extra></extra>"))
    fig.update_layout(height=720, hovermode="closest")
    fig.update_xaxes(title="Late rate")
    add(fig, "Late rate by destination state",
        "Denominator: delivered orders holding both a delivery date and an estimate. "
        "Hover for the group size behind each rate.")

    buckets = load("reviews_by_delay_bucket.csv")
    fig = go.Figure(go.Bar(
        x=[b.split(". ", 1)[1] for b in buckets["delay_bucket"]], y=buckets["pct_1_2_star"],
        marker_color=[CRITICAL if "late" in b else SERIES_1 for b in buckets["delay_bucket"]],
        customdata=buckets[["n_orders", "mean_review_score"]],
        hovertemplate="<b>%{x}</b><br>1-2 star %{y:.2f}%<br>"
                      "Orders %{customdata[0]:,}<br>Mean score %{customdata[1]:.2f}<extra></extra>"))
    fig.update_layout(hovermode="closest")
    fig.update_yaxes(title="Share rated 1 or 2 stars")
    add(fig, "Review scores against delivery punctuality",
        "Association, not causation. The same underlying problem can produce both the delay "
        "and the low score.")

    dist = load("delay_distribution.csv")
    fig = go.Figure(go.Bar(
        x=dist["delay_days"], y=dist["n_orders"],
        marker_color=[CRITICAL if d > 0 else SERIES_1 for d in dist["delay_days"]],
        hovertemplate="%{x} days<br>%{y:,} orders<extra></extra>"))
    fig.update_xaxes(title="Days from promised date (negative = early)")
    fig.update_yaxes(title="Orders")
    add(fig, "Distribution of delivery timing",
        "Trimmed to plus or minus 40 days. The median order arrives 12 days early.")

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Olist — delivery and satisfaction</title>
<style>
  body {{ margin:0; background:#f9f9f7; color:{INK};
         font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
  main {{ max-width:1040px; margin:0 auto; padding:32px 20px 64px; }}
  h1 {{ font-size:26px; margin:0 0 6px; }}
  .lede {{ color:{INK_SECONDARY}; margin:0 0 28px; max-width:70ch; line-height:1.55; }}
  section {{ background:{SURFACE}; border:1px solid rgba(11,11,11,0.10);
             border-radius:10px; padding:20px 18px 8px; margin-bottom:22px; }}
  h2 {{ font-size:17px; margin:0 0 4px; }}
  .note {{ color:{INK_SECONDARY}; font-size:13px; margin:0 0 10px; max-width:75ch; line-height:1.5; }}
  footer {{ color:{MUTED}; font-size:12px; margin-top:28px; line-height:1.6; }}
</style></head><body><main>
<h1>Olist — sales, delivery performance and satisfaction</h1>
<p class="lede">Brazilian marketplace, 2017-01 to 2018-08. Every figure below is generated
from <code>dashboard/exports/</code>, which is reconciled against the DuckDB model at export
time. Group sizes appear on hover so no rate can be read without its denominator.</p>
{''.join(blocks)}
<footer>Item value, shipping and payments are three different measures and none of them is
profit: this dataset contains no cost, tax, refund or commission data.<br>
Relationships shown are associations, not causal effects.<br>
Data: Olist Brazilian E-Commerce, CC BY-NC-SA 4.0. Only aggregates are published here.</footer>
</main></body></html>"""

    out.write_text(page, encoding="utf-8")
    size_mb = out.stat().st_size / 1_048_576
    print(f"  wrote {out.relative_to(PROJECT_ROOT)} ({size_mb:.1f} MB, self-contained)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--png", action="store_true")
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()
    do_all = not (args.png or args.html)
    if args.png or do_all:
        build_png()
    if args.html or do_all:
        build_html()
