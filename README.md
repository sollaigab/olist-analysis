# Olist — Sales, Delivery Performance and Customer Satisfaction

Reproducible analysis of the Olist Brazilian e-commerce dataset (~100k orders,
2016–2018), covering item revenue over time, delivery delays by category and
region, and the relationship between lateness and review scores.

**Stack**: DuckDB + SQL · Python/pandas · pytest · Power BI (and a
browser-viewable HTML/matplotlib alternative).

> Status: work in progress. Milestone 1 of 5 complete (scaffold + ingest).

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
dashboard/     Power BI file, screenshots, and the CSV exports that feed it
reports/       final report and figures
```

## Reproduction

```bash
# 1. Dependencies
python -m pip install -r requirements.txt

# 2. Data (see data/README.md for the manual alternative)
python src/ingest.py --download

# 3. Build the modelled layers
python src/build.py          # milestone 3

# 4. Tests
python -m pytest -q          # milestone 2+

# 5. Dashboard-ready aggregates
python src/export_bi.py      # milestone 4
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

| MCP server | Role in this project |
|---|---|
| IDE (`executeCode`) | Runs Python in a persistent Jupyter kernel, so the DuckDB connection and intermediate DataFrames survive between exploration steps |
| IDE (`getDiagnostics`) | Static error/lint feedback on notebooks and `src/*.py` |
| Claude Docs | Drafting surface for the final report |

No MCP server exists for DuckDB or Power BI; those are driven locally by the
scripts in `src/`. This table is deliberately accurate about which tools were
actually used.

## Licence

Code: MIT. Data: CC BY-NC-SA 4.0 — see `data/README.md`.
