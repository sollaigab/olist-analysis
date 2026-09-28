"""Render the static report figures from the exported aggregates.

Charts are built from dashboard/exports/*.csv, not from fresh queries, so these
figures, the interactive dashboard and Power BI all show the same numbers.

Output: reports/figures/*.png, used by reports/report.md.
The interactive version is a separate script, src/make_dashboard.py.

Conventions:
  - One y-axis per chart. Two measures at different scales get two charts.
  - Group sizes on the chart, not in a footnote.
  - Two-slot categorical palette, checked for colour-vision separation. Nothing
    relies on colour alone; multi-series charts are directly labelled too.

Usage:
    python src/make_charts.py
"""

from __future__ import annotations

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


def fig_state_late_rate_ci() -> None:
    """Forest plot. The interval is the point of the chart, not decoration."""
    df = load("state_late_rate_ci.csv").sort_values("late_rate_pct")
    national = df["national_rate_pct"].iloc[0]
    fig, ax = plt.subplots(figsize=(8.6, 8.6))
    y = range(len(df))
    colors = [CRITICAL if v == "worse than national"
              else SERIES_1 if v == "better than national"
              else MUTED
              for v in df["verdict"]]
    for i, (_, row) in enumerate(df.iterrows()):
        ax.plot([row["ci_lower_pct"], row["ci_upper_pct"]], [i, i],
                color=colors[i], linewidth=2.2, solid_capstyle="round", zorder=2)
    ax.scatter(df["late_rate_pct"], y, color=colors, s=34, zorder=3,
               edgecolor=SURFACE, linewidth=1.2)
    ax.axvline(national, color=INK_SECONDARY, linestyle=":", linewidth=1.4, zorder=1)
    ax.text(national + 0.4, len(df) - 0.5, f"national {national:.2f}%",
            color=INK_SECONDARY, fontsize=9)
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{s}  n={int(n):,}" for s, n in
                        zip(df["customer_state"], df["n_orders"])], fontsize=8.6)
    ax.set_xlabel("Late rate with 95% Wilson interval")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_xlim(0, df["ci_upper_pct"].max() * 1.12)
    ax.grid(axis="x", alpha=0.9)
    ax.grid(axis="y", visible=False)
    n_worse = int((df["verdict"] == "worse than national").sum())
    n_same = int((df["verdict"] == "not distinguishable").sum())
    finish(ax, "Six states cannot be told apart from the national rate",
           f"{n_worse} states are distinguishably worse, {n_same} are not distinguishable "
           "at all · grey = interval crosses the national rate",
           "Source: mart.kpi_state_late_rate_ci. Wilson score interval, 95%. The interval "
           "covers sampling variability only; it says nothing about whether the sample "
           "represents the marketplace or whether 2018 resembles today.")
    ax.grid(axis="y", visible=False)
    save(fig, "08_state_late_rate_ci.png")


def fig_cohort_retention() -> None:
    df = load("cohort_retention_90d.csv")
    df["cohort_month"] = pd.to_datetime(df["cohort_month"])
    # Tiny early cohorts (2 and 1 customers) carry intervals 60+ points wide and
    # would dominate the y-axis without saying anything.
    df = df[df["n_new_customers"] >= 100].reset_index(drop=True)
    complete = df[df["is_complete"]]
    censored = df[~df["is_complete"]]
    pooled = 100.0 * complete["n_repeated_within_90d"].sum() / complete["n_new_customers"].sum()

    fig, ax = plt.subplots(figsize=(9.4, 4.8))
    ax.fill_between(complete["cohort_month"], complete["ci_lower_pct"],
                    complete["ci_upper_pct"], color=SERIES_1, alpha=0.16, linewidth=0)
    ax.plot(complete["cohort_month"], complete["repeat_rate_90d_pct"],
            color=SERIES_1, linewidth=2, marker="o", markersize=4,
            markerfacecolor=SURFACE, markeredgewidth=1.4, markeredgecolor=SERIES_1)
    ax.plot(censored["cohort_month"], censored["repeat_rate_90d_pct"],
            color=MUTED, linewidth=2, linestyle="--", marker="o", markersize=4,
            markerfacecolor=SURFACE, markeredgewidth=1.4, markeredgecolor=MUTED)
    ax.axhline(pooled, color=CRITICAL, linestyle=":", linewidth=1.4)
    ax.set_ylabel("Share ordering again within 90 days")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    top = max(4.0, df["ci_upper_pct"].max() * 1.1)
    ax.set_ylim(0, top)

    # The series never rises above ~3.2% after the first few months, so the
    # upper-right of the plot is genuinely empty. Both labels go there with
    # leader lines rather than sitting on top of the data.
    ax.annotate(f"dotted line: {pooled:.2f}% pooled\nacross complete cohorts",
                (complete["cohort_month"].iloc[-3], pooled),
                xytext=(complete["cohort_month"].iloc[-1], top * 0.90),
                textcoords="data", ha="right", color=CRITICAL, fontsize=8.8,
                arrowprops=dict(arrowstyle="-", color=CRITICAL, linewidth=0.8, alpha=0.6))
    if len(censored):
        ax.annotate("censored: fewer than\n90 days of observation",
                    (censored["cohort_month"].iloc[0],
                     censored["repeat_rate_90d_pct"].iloc[0]),
                    xytext=(censored["cohort_month"].iloc[-1], top * 0.62),
                    textcoords="data", ha="right", color=MUTED, fontsize=8.8,
                    arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.8))
    finish(ax, "Almost nobody comes back",
           "97.0% of customers placed exactly one order · shaded band is the 95% "
           "Wilson interval · dashed cohorts have not lived a full 90 days",
           "Source: mart.kpi_cohort_retention_90d. Cohorts under 100 customers omitted. "
           "Counted per customer_unique_id, the person - customer_id would count the same "
           "person twice. Dataset ends 2018-09-03, which is what censors the last cohorts.")
    save(fig, "09_cohort_retention.png")


FIGURES = [
    fig_sales_monthly,
    fig_aov_monthly,
    fig_late_rate_by_state,
    fig_delay_distribution,
    fig_reviews_by_delay,
    fig_category_priority,
    fig_late_rate_monthly,
    fig_state_late_rate_ci,
    fig_cohort_retention,
]


def build_png() -> None:
    print("Rendering figures:")
    for figure in FIGURES:
        figure()


if __name__ == "__main__":
    build_png()
