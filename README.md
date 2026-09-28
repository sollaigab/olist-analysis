# Olist — sales, delivery performance and customer satisfaction

[![tests](https://github.com/sollaigab/olist-analysis/actions/workflows/tests.yml/badge.svg)](https://github.com/sollaigab/olist-analysis/actions/workflows/tests.yml)

Analysis of ~100k orders from the Olist Brazilian marketplace (2016–2018): how
item value moved over time, where delivery delays concentrate, and how review
scores relate to late deliveries.

Built with DuckDB and SQL, Python/pandas for exploration, pytest for checks, and
a browser-viewable dashboard (plus a Power BI build sheet).

The dashboard has four sections, a KPI row whose tiles each state their
denominator, a state filter that cross-filters the logistics charts, a table view
behind every chart, and a light/dark toggle. Every rate carries its group size on
hover.

**[Findings →](reports/report.md)** · **[Interactive charts →](https://sollaigab.github.io/olist-analysis/)**

![Monthly late rate](reports/figures/07_late_rate_monthly.png)

Three months out of twenty account for 48.4% of every late delivery. And the
orders customers rated worst were six times *less* likely to be late than
average — so delivery speed only explains part of the dissatisfaction.

![Late rate by destination state](reports/figures/03_late_rate_by_state.png)

---

## Questions

1. How does the value of sold items change over time?
2. Which categories and regions concentrate delivery delays?
3. How do review scores differ between on-time and late orders?
4. What deserves attention once you weigh rate against volume?

Plus one I added later: how much repeat purchasing is there? (Short answer: very
little — 97% of customers ordered once.)

## Layout

```
data/          provenance and licence notes (raw data is not versioned)
src/           ingest, build, export and chart scripts
sql/           00_staging -> 10_quality -> 20_intermediate -> 30_marts -> 40_kpi
notebooks/     exploratory analysis
tests/         grain, KPI reconciliation, report figures, and a synthetic-data
               suite that runs in CI without the licensed dataset
dashboard/     exports/ (CSV aggregates), olist_dashboard.html, Power BI build spec
docs/          GitHub Pages build of the dashboard (plotly from CDN, ~170 KB)
reports/       data dictionary, quality report, figures, final report
```

## Running it

```bash
python -m pip install -r requirements.txt

python src/ingest.py --download   # or place the CSVs yourself, see data/README.md
python src/build.py               # runs the SQL layers in order
python -m pytest -q

python src/profile_columns.py     # regenerates reports/data_dictionary.md
python src/quality_report.py      # regenerates reports/quality_report.md
python src/export_bi.py           # CSV aggregates for the dashboard
python src/make_charts.py         # static figures for the report
python src/make_dashboard.py      # interactive dashboard, local + Pages
```

The database lands at `data/olist.duckdb` and is rebuilt from scratch by the
ingest step. Delete it, run the steps again, and every generated file comes back
byte-identical, apart from the generation date stamped in the dashboard footer —
I check this before each commit, because getting it wrong once
was how I found four sources of nondeterminism (unstable `ORDER BY` ties, a
`DISTINCT … LIMIT` with no ordering, unordered table renders, and plotly's random
div ids).

`tests/test_report_figures.py` pins the numbers quoted in `reports/report.md`.
If the data or the report changes without the other, the suite fails.

## How I worked with the data

A few rules I held the whole project to, mostly because ignoring any of them is
how e-commerce analyses go quietly wrong:

- **Declare the grain of every table, then test it.** Orders, items, payments and
  reviews all live at different grains. They get aggregated separately and joined
  only at one-row-per-order, so no join can multiply an amount.
- **`customer_id` is not `customer_unique_id`.** The first is per-order, the
  second is the person. Customer counts use the second.
- **Item value, freight and payments are three separate measures**, and none of
  them is profit. There's no cost or refund data here.
- **Every KPI states its filter and its denominator**, including how
  cancellations, missing timestamps and duplicate reviews are handled.
- **Every comparison shows its group sizes**, and rates carry 95% Wilson
  intervals. A 21.5% rate on 396 orders shouldn't read like a 4.5% rate on
  40,399. Six of 27 states turn out not to be distinguishable from the national
  rate at all.
- **Cohorts use a fixed observation window** and censored ones are flagged, so
  the tail of the retention curve isn't mistaken for a decline.
- **Associations aren't causes.** Late deliveries and low scores co-occur; the
  report says so and stops there.
- **A review of a multi-seller order isn't attributed to one seller.**

Four of these caught mistakes I'd already made — a `review_id` I'd assumed was a
primary key and isn't, a benchmark hardcoded at one denominator and drawn against
another, a claim about category spread that was wrong in the flattering
direction, and a category I dismissed as noise that the confidence interval says
is real. They're in the commit history rather than quietly amended.

## AI assistance

I built this with Claude Code as a pair programmer. It scaffolded the repo,
drafted a lot of the SQL and Python, and proposed the first cut of the KPI
definitions. The analytical calls are mine: collapsing multiple reviews to the
most recent one, measuring lateness at date rather than timestamp granularity,
trimming the series to 2017-01–2018-08, refusing to attribute multi-seller
reviews, and declining to put a revenue figure on the delay problem when the data
can't support one.

Every number in `reports/` comes from a query that was actually run against the
local database. Nothing is quoted from a model's prior knowledge of this dataset,
and the test suite exists partly to keep it that way.

On MCP servers, for anyone curious: the IDE `executeCode` server needs an open
notebook editor in VS Code, and this was built from a terminal, so it never ran —
`notebooks/01_eda.ipynb` was executed headlessly with `nbclient` instead and
carries real outputs. There's no MCP server for DuckDB, Power BI or Kaggle; those
are the Python library, the desktop app, and the Kaggle API client respectively.

## CI

The dataset is CC BY-NC-SA and can't be committed, so the Olist-specific
assertions skip when `data/olist.duckdb` is absent. What does run on every push
is the whole SQL pipeline against [`tests/synthetic.py`](tests/synthetic.py) — a
small made-up fixture that reproduces each defect shape from the real source: a
multi-seller order, a doubly-reviewed order, a `review_id` shared across two
orders, a split payment, a cancelled order with no items, a delivered order with
no delivery date, a zip prefix with a leading zero.

That gives 31 tests covering grain, money conservation and defect handling
without any licensed data present. The workflow also fails if a dataset file ever
gets tracked in git.

## Licence

Code: MIT, see [`LICENSE`](LICENSE). The dataset is published by Olist under
CC BY-NC-SA 4.0 and isn't redistributed here — no raw records are versioned. The
aggregates in `dashboard/exports/` are derived summaries and stay subject to the
dataset's terms, including the non-commercial restriction. See
[`data/README.md`](data/README.md).

---
