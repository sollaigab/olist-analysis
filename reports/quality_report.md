# Data quality report

Generated from `data/olist.duckdb` on 2026-09-28 by `src/quality_report.py`. Regenerate after any change to `sql/00_staging/` or `sql/10_quality/`.

The counts below are asserted in `tests/test_grain.py`: known defects are frozen as a baseline so the suite fails when the *data* changes, rather than staying permanently red.

## Cast audit

A non-zero `failed_casts` means an explicit cast turned a real value into NULL. `blank_source` counts values that were already absent in the CSV.

| column_checked | failed_casts | blank_source |
|---|---|---|
| geolocation.geolocation_lat | 0 | 0 |
| order_items.freight_value | 0 | 0 |
| order_items.price | 0 | 0 |
| order_payments.payment_value | 0 | 0 |
| order_reviews.review_score | 0 | 0 |
| orders.order_approved_at | 0 | 160 |
| orders.order_delivered_carrier_date | 0 | 1,783 |
| orders.order_delivered_customer_date | 0 | 2,965 |
| orders.order_estimated_delivery_date | 0 | 0 |
| orders.order_purchase_timestamp | 0 | 0 |

## Declared keys and cardinality

`duplicate_rows` is expected to be 0 where the expectation says *unique*, and greater than 0 where it says *NOT unique* — a one-to-many relationship that turned out to be one-to-one would be just as much of a surprise.

| declared_key | rows | distinct_keys | duplicate_rows | expectation |
|---|---|---|---|---|
| stg.customers / customer_id | 99,441 | 99,441 | 0 | unique |
| stg.customers / customer_unique_id | 99,441 | 96,096 | 3,345 | NOT unique (repeat buyers) |
| stg.geolocation / zip_prefix | 19,015 | 19,015 | 0 | unique |
| stg.order_items / (order_id, order_item_id) | 112,650 | 112,650 | 0 | unique |
| stg.order_items / order_id | 112,650 | 98,666 | 13,984 | NOT unique (fan-out) |
| stg.order_payments / (order_id, payment_sequential) | 103,886 | 103,886 | 0 | unique |
| stg.order_payments / order_id | 103,886 | 99,440 | 4,446 | NOT unique (split payments) |
| stg.order_reviews / order_id | 99,224 | 98,673 | 551 | NOT unique (multiple reviews) |
| stg.order_reviews / review_id | 99,224 | 98,410 | 814 | unique |
| stg.orders / order_id | 99,441 | 99,441 | 0 | unique |
| stg.products / product_id | 32,951 | 32,951 | 0 | unique |
| stg.sellers / seller_id | 3,095 | 3,095 | 0 | unique |

## Referential integrity

Orphans are counted, not assumed away. Rows noted *must be 0* are hard failures; the rest are documented characteristics of the dataset.

| relationship | n_orphans | note |
|---|---|---|
| orders without any item | 775 | expected for unavailable/canceled orders |
| orders without any review | 768 | drives the review-coverage denominator |
| products with no category at all | 610 | bucketed as unknown downstream |
| customer zip prefixes absent from geolocation | 157 | limits map coverage, not order counts |
| products with an untranslatable category | 2 | category stays in Portuguese for these |
| orders without any payment | 1 | investigate individually if small |
| items pointing at a missing order | 0 | must be 0 |
| items pointing at a missing product | 0 | must be 0 |
| items pointing at a missing seller | 0 | must be 0 |
| orders pointing at a missing customer | 0 | must be 0 |
| reviews pointing at a missing order | 0 | must be 0 |

## Business rules

`FAIL` contradicts the model and is excluded or flagged downstream. `INFO` is a genuine property of the data that shapes how KPIs are built.

| rule | n_rows | status | handling |
|---|---|---|---|
| delivery to customer earlier than handover to carrier | 23 | FAIL | physically impossible ordering; flagged, excluded from lead-time medians |
| delivered orders missing a delivery date | 8 | FAIL | status says delivered but the timestamp is absent; excluded from all delay KPIs |
| approval earlier than purchase | 0 | FAIL | must be 0 |
| delivery earlier than purchase | 0 | FAIL | must be 0 |
| freight value < 0 | 0 | FAIL | must be 0 |
| item price <= 0 | 0 | FAIL | must be 0 for a marketplace sale |
| repeat customers (customer_unique_id with >1 order) | 2,997 | INFO | why customer counts must use customer_unique_id, not customer_id |
| orders fulfilled by more than one seller | 1,278 | INFO | excluded from any seller-level review attribution |
| review_id reused across different orders | 789 | INFO | review_id is NOT a primary key; the grain is (review_id, order_id) |
| orders carrying more than one review | 547 | INFO | collapsed to one review per order in 20_intermediate; rule documented there |
| orders in sparse boundary months (before 2017-01 or after 2018-08) | 349 | INFO | partial months at both ends; time series is trimmed to 2017-01..2018-08 |
| payment value <= 0 | 9 | INFO | zero-value payment lines (vouchers covering the full amount); kept, never used as revenue |
