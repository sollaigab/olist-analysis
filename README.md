# Olist — Sales, Delivery Performance and Customer Satisfaction

Reproducible analysis of the Olist Brazilian e-commerce dataset (~100k orders,
2016–2018), covering item revenue over time, delivery delays by category and
region, and the relationship between lateness and review scores.

**Stack**: DuckDB + SQL · Python/pandas · pytest · Power BI (and a
browser-viewable HTML/matplotlib alternative).

> Status: work in progress. Milestones 1-4 of 5 complete (scaffold, model, KPIs, exploration and charts). Remaining: dashboard and report.

---

## Business questions

1. How does the value of sold items evolve over time?
2. Which product categories and geographic areas concentrate delivery delays?
3. How do review scores differ between on-time and late orders?
4. Which issues deserve attention once both rate **and** volume are considered?

## Repository layout

```
data/          provenance and licence notes (raw data is NOT versioned)
src/           ingest, build and export scripts
sql/           00_staging -> 10_quality -> 20_intermediate -> 30_marts -> 40_kpi
notebooks/     exploratory analysis
tests/         grain, key-uniqueness and KPI reconciliation tests
dashboard/     exports/ (CSV aggregates), olist_charts.html, Power BI file, screenshots
reports/       data dictionary, quality report, figures, final report
```

## Reproduction

```bash
# 1. Dependencies
python -m pip install -r requirements.txt

# 2. Data (see data/README.md for the manual alternative)
python src/ingest.py --download

# 3. Build the modelled layers (staging -> quality -> intermediate -> marts -> KPI)
python src/build.py

# 4. Tests
python -m pytest -q

# 5. Regenerate the generated documents
python src/profile_columns.py   # reports/data_dictionary.md
python src/quality_report.py    # reports/quality_report.md

# 6. Dashboard-ready aggregates, each reconciled against its source view
python src/export_bi.py

# 7. Figures and the standalone interactive page
python src/make_charts.py
```

The DuckDB database lands at `data/olist.duckdb` and is rebuilt from scratch by
step 2; nothing downstream depends on manual state.

## Analytical conventions

These are the rules the whole project is held to:

- **Grain is declared for every table.** Orders, items, payments and reviews
  live at different grains; they are aggregated separately and joined only at
  one-row-per-order grain, so amounts are never multiplied by a join.
- **`customer_id` ≠ `customer_unique_id`.** The first is per-order, the second
  is the person. Customer counts use the second; joins use the first.
- **Item value, freight and payments are three different measures.** None of
  them is profit, and the project never calls them that.
- **Every KPI states its filter and its denominator**, including how
  cancellations, missing timestamps and duplicate reviews are handled, and how
  many rows each rule removed.
- **Every comparison reports its group sizes.**
- **Associations are not causes.** Late deliveries correlating with low review
  scores is reported as an association.
- **A review of a multi-seller order is not attributed to one seller.**

## AI usage

This project was developed with Claude Code as a pair-programming assistant.
Claude scaffolded the repository, drafted SQL and Python, and proposed the KPI
definitions; every figure quoted in `reports/` comes from a query that was
actually executed against the local database, not from the assistant's prior
knowledge of the dataset. Model Context Protocol (MCP) servers were used as
follows:

| MCP server | Status in this project |
|---|---|
| IDE (`executeCode`) | **Available but not used.** It requires an open notebook editor in VS Code; the session ran from a terminal, so the call returned `No active notebook editor found`. The notebook was instead generated and executed headlessly with `nbclient`, which stores real outputs in `notebooks/01_eda.ipynb`. Opening that notebook in VS Code makes this MCP server usable for live kernel work. |
| IDE (`getDiagnostics`) | Available; same editor requirement. |
| Claude Docs | Available; the report is written as a Markdown file in `reports/` instead. |

**There is no MCP server for DuckDB, Power BI or Kaggle.** Those are driven by
the scripts in `src/`: `duckdb` as a Python library, the Kaggle API client for
the download, and Power BI opened by hand against `dashboard/exports/`.

This table lists what was actually used rather than what would sound good. A
tool that was available but did not run is recorded as not used.

## Licence

Code: MIT. Data: CC BY-NC-SA 4.0 — see `data/README.md`.
