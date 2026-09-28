# Power BI build specification

**This file is a build sheet, not a record of something already built.** Power BI
Desktop was not installed on the machine this project was developed on, so the
`.pbix` does not exist in the repository yet. Everything it needs does: the
fourteen reconciled CSVs in `dashboard/exports/`.

Follow this sheet and the dashboard will show exactly the numbers in
`reports/report.md` and `reports/figures/`, because all three read the same
exports.

> If you never install Power BI, `dashboard/olist_dashboard.html` covers the same
> ground interactively and opens in any browser — same four sections, same
> numbers, same exports underneath.

---

## 0. Before you start

Power BI Desktop is **free**. A Pro licence is only needed to *publish* to the
Power BI Service and share online; building, opening and screenshotting a
`.pbix` locally costs nothing.

Save the file as `dashboard/olist.pbix`. It is gitignored — `.pbix` files grow
past GitHub's comfortable limits — so commit **screenshots** to
`dashboard/screenshots/` instead. That is also what a recruiter can actually
look at without installing anything.

## 1. Load the data

`Home → Get data → Text/CSV`, then load every file in `dashboard/exports/`
except `_manifest.csv` (keep that one out of the model; it is documentation).

In Power Query, for each table:

1. Check that `purchase_month` came in as **Date**, not Text.
2. Check that every `*_pct` and `*_value` column is **Decimal Number**.
3. Leave `customer_state` and `seller_state` as **Text**.

Do not merge tables in Power Query. The aggregation was done in SQL precisely so
the BI layer would not have to guess at a join.

## 2. Model

These exports are **pre-aggregated at different grains**, so this is not a star
schema and must not be wired up as one. Each table answers one question on its
own page. The only shared dimension worth creating is a date table for the
monthly pages.

```
Modeling → New table
Date = CALENDAR(DATE(2017,1,1), DATE(2018,8,31))
```

Add a `Month` column, mark it as a date table, and relate it **one-to-many** to:

- `sales_monthly[purchase_month]`
- `late_rate_monthly[purchase_month]`
- `review_coverage_monthly[purchase_month]`
- `payment_mix_monthly[purchase_month]`
- `late_rate_state_monthly[purchase_month]`

Leave `delay_by_state`, `delay_by_category`, `category_priority`,
`state_priority`, `reviews_by_punctuality`, `reviews_by_delay_bucket`,
`delay_distribution` and `delay_by_seller_state` **unrelated**. They are
standalone summaries. Relating them to the date table would silently let a date
slicer filter a table that has no date column, which produces blanks rather than
an error.

## 3. Measures

Every measure below re-derives a rate from its own numerator and denominator.
**Never average a percentage column** — averaging `late_rate_pct` across states
weights a 396-order state equally with a 40,399-order one.

```dax
Orders = SUM(late_rate_monthly[n_orders])

Late orders = SUM(late_rate_monthly[n_late_orders])

Late rate =
DIVIDE(
    SUM(late_rate_monthly[n_late_orders]),
    SUM(late_rate_monthly[n_orders])
)

Item value = SUM(sales_monthly[items_value])

Freight value = SUM(sales_monthly[freight_value])

-- AOV is recomputed, not averaged: SUM/SUM, never AVERAGE(aov)
AOV =
DIVIDE(
    SUM(sales_monthly[items_value]),
    SUM(sales_monthly[n_orders])
)

Freight share of item value =
DIVIDE(
    SUM(sales_monthly[freight_value]),
    SUM(sales_monthly[items_value])
)

Review coverage =
DIVIDE(
    SUM(review_coverage_monthly[n_reviewed]),
    SUM(review_coverage_monthly[n_sale_eligible_orders])
)

State late rate =
DIVIDE(
    SUM(state_priority[n_late_orders]),
    SUM(state_priority[n_orders])
)

Excess late orders = SUM(state_priority[excess_late_orders])
```

Format `Late rate`, `Review coverage` and `Freight share of item value` as
**Percentage, 2 decimal places**. Format `Item value` and `AOV` as **Decimal,
thousands separator**, and label the axis **BRL** — not `$`.

## 4. Pages

### Page 1 — Overview

| Visual | Source | Notes |
|---|---|---|
| Card: `Item value` | `sales_monthly` | Subtitle must read "merchandise only, shipping excluded" |
| Card: `Orders` | `late_rate_monthly` | |
| Card: `AOV` | measure | |
| Card: `Freight share of item value` | measure | |
| Line: `Item value` by month | `sales_monthly` | |
| Line: `AOV` and `Average item price` by month | `sales_monthly` | Both in BRL, **one shared axis** |
| Stacked column: orders by `dominant_payment_type` | `payment_mix_monthly` | Max 5 categories, no "other" bucket needed |
| Date slicer | `Date` table | |

**Do not put item value and AOV on one chart with two y-axes.** Different
scales, and a dual axis lets the reader infer a relationship from crossing
lines that is an artefact of axis scaling. Two charts, always.

### Page 2 — Logistics

| Visual | Source | Notes |
|---|---|---|
| Card: `Late rate` | measure | Subtitle: "delivered orders holding both a delivery date and an estimate" |
| Card: `Late orders` | measure | |
| Column: `Late rate` by month | `late_rate_monthly` | Highlight 2017-11, 2018-02, 2018-03 |
| Bar: `State late rate` by `customer_state` | `state_priority` | Sort descending; **add `n_orders` as a tooltip field** |
| Scatter: `n_orders` (x, log) vs `late_rate_pct` (y) | `category_priority` | Bubble size = `items_value` |
| Table: state, n_orders, n_late_orders, late_rate_pct, median_delivery_days, median_handover_days | `state_priority` | The table view is the accessibility fallback for the bar chart |
| Matrix: state × month heat of `late_rate_pct` | `late_rate_state_monthly` | Groups under 30 orders are already excluded by the export |

Every rate visual on this page must carry `n_orders` in its tooltip. A state
bar showing 21.5% on 396 orders and one showing 12.1% on 12,310 orders look
identical otherwise, and they are not the same finding.

### Page 3 — Reviews

| Visual | Source | Notes |
|---|---|---|
| Card: mean review score | `reviews_by_punctuality` | |
| Card: `Review coverage` | measure | |
| Column: `pct_1_2_star` by `delay_bucket` | `reviews_by_delay_bucket` | Sorted by the bucket's leading digit, not alphabetically |
| Clustered bar: mean score, on time vs late | `reviews_by_punctuality` | Show `n_orders` as a data label |
| Line: mean review score by month | `late_rate_monthly` | |
| Text box | — | **Required.** See wording below. |

The text box is not optional decoration:

> These are associations, not causal effects. A difficult route, a slow seller or
> a stock problem can produce both a late delivery and a low score. Roughly a
> third of all 1–2 star reviews sit on late orders; the rest do not.

### Page 4 (optional) — Definitions

Table visual over `kpi_definitions`, showing `kpi`, `definition`,
`filter_applied`, `denominator`, `caveat`. Anyone who asks "what's in this
number?" gets the answer without asking you.

## 5. Sanity checks before you screenshot

Run these and compare against the database. If any disagrees, the visual is
wrong, not the data.

| Check | Expected |
|---|---|
| Overview `Item value`, full range | 13,449,529.68 |
| Overview `Orders`, full range | 96,203 |
| Logistics `Late rate`, full range | 6.79% |
| Logistics `Late orders`, full range | 6,531 |
| Reviews `Review coverage`, full range | 99.26% |
| Bar chart: does any state show a rate on fewer than 100 orders without its n visible? | No |
| Any chart with two y-axes? | No |
| Any percentage produced by `AVERAGE()` of a `_pct` column? | No |

The first four come straight from `dashboard/exports/`; a mismatch almost always
means a slicer is still applied or a measure used `AVERAGE` where it needed
`DIVIDE(SUM, SUM)`.

## 6. Screenshots

Export one PNG per page to `dashboard/screenshots/` as `01_overview.png`,
`02_logistics.png`, `03_reviews.png`. Those are what the README links to, and
what someone without Power BI will actually see.
