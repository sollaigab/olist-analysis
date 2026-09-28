# Data dictionary — staging layer

Generated from `data/olist.duckdb` on 2026-09-28 by `src/profile_columns.py`. Every figure below is the output of a query run at generation time; nothing here is transcribed by hand.

Column names are the **staged** names. Where a staged name differs from the source CSV column, the source name is given in the notes so lineage stays traceable.

## `stg.orders`

- **Grain**: 1 row = 1 order
- **Key**: `order_id`
- **Rows**: 99,441

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `order_id` | VARCHAR | 0 | 0.0% | 99,441 | 00010242fe8c5a6d1ba2dd792c…, 00018f77f2f0320c557190d7a1…, 000229ec398224ef6ca0657da4… |
| `customer_id` | VARCHAR | 0 | 0.0% | 99,441 | 00012a2ce6f8dcda20d059ce98…, 000161a058600d5901f007fab4…, 0001fd6190edaaf884bcaf3d49… |
| `order_status` | VARCHAR | 0 | 0.0% | 8 | approved, canceled, created |
| `purchased_at` | TIMESTAMP | 0 | 0.0% | 98,875 | 2016-09-04 21:15:19, 2016-09-05 00:15:34, 2016-09-13 15:24:19 |
| `approved_at` | TIMESTAMP | 160 | 0.2% | 90,733 | 2016-09-15 12:16:38, 2016-10-04 09:43:32, 2016-10-04 10:18:57 |
| `delivered_carrier_at` | TIMESTAMP | 1,783 | 1.8% | 81,018 | 2016-10-08 10:34:01, 2016-10-08 13:46:32, 2016-10-08 14:46:49 |
| `delivered_customer_at` | TIMESTAMP | 2,965 | 3.0% | 95,664 | 2016-10-11 13:46:32, 2016-10-11 14:46:49, 2016-10-13 03:10:34 |
| `estimated_delivery_at` | TIMESTAMP | 0 | 0.0% | 459 | 2016-09-30 00:00:00, 2016-10-04 00:00:00, 2016-10-20 00:00:00 |

## `stg.order_items`

- **Grain**: 1 row = 1 item line within an order
- **Key**: `(order_id, order_item_id)`
- **Rows**: 112,650

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `order_id` | VARCHAR | 0 | 0.0% | 98,666 | 00010242fe8c5a6d1ba2dd792c…, 00018f77f2f0320c557190d7a1…, 000229ec398224ef6ca0657da4… |
| `order_item_id` | INTEGER | 0 | 0.0% | 21 | 1, 2, 3 |
| `product_id` | VARCHAR | 0 | 0.0% | 32,951 | 00066f42aeeb9f3007548bb9d3…, 00088930e925c41fd95ebfe695…, 0009406fd7479715e4bef61dd9… |
| `seller_id` | VARCHAR | 0 | 0.0% | 3,095 | 0015a82c2db000af6aaaf3ae2e…, 001cca7ae9ae17fb1caed9dfb1…, 001e6ad469a905060d959994f1… |
| `shipping_limit_at` | TIMESTAMP | 0 | 0.0% | 93,318 | 2016-09-19 00:15:34, 2016-09-19 23:11:33, 2016-10-08 10:34:01 |
| `item_price` | DECIMAL(12,2) | 0 | 0.0% | 5,968 | 0.85, 1.20, 2.20 |
| `freight_value` | DECIMAL(12,2) | 0 | 0.0% | 6,999 | 0.00, 0.01, 0.02 |

## `stg.order_payments`

- **Grain**: 1 row = 1 payment instrument on an order
- **Key**: `(order_id, payment_sequential)`
- **Rows**: 103,886

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `order_id` | VARCHAR | 0 | 0.0% | 99,440 | 00010242fe8c5a6d1ba2dd792c…, 00018f77f2f0320c557190d7a1…, 000229ec398224ef6ca0657da4… |
| `payment_sequential` | INTEGER | 0 | 0.0% | 29 | 1, 2, 3 |
| `payment_type` | VARCHAR | 0 | 0.0% | 5 | boleto, credit_card, debit_card |
| `payment_installments` | INTEGER | 0 | 0.0% | 24 | 0, 1, 2 |
| `payment_value` | DECIMAL(12,2) | 0 | 0.0% | 29,077 | 0.00, 0.01, 0.03 |

## `stg.order_reviews`

- **Grain**: 1 row = 1 review of 1 order
- **Key**: `(review_id, order_id)`
- **Rows**: 99,224

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `review_id` | VARCHAR | 0 | 0.0% | 98,410 | 0001239bc1de2e33cb583967c2…, 0001cc6860aeaf5b9017fe4131…, 00020c7512a52e92212f12d3e3… |
| `order_id` | VARCHAR | 0 | 0.0% | 98,673 | 00010242fe8c5a6d1ba2dd792c…, 00018f77f2f0320c557190d7a1…, 000229ec398224ef6ca0657da4… |
| `review_score` | SMALLINT | 0 | 0.0% | 5 | 1, 2, 3 |
| `review_comment_title` | VARCHAR | 87,656 | 88.3% | 4,527 |  ,  10,  4  |
| `review_comment_message` | VARCHAR | 58,247 | 58.7% | 36,159 | 
, 

, 









 |
| `review_created_at` | TIMESTAMP | 0 | 0.0% | 636 | 2016-10-02 00:00:00, 2016-10-06 00:00:00, 2016-10-09 00:00:00 |
| `review_answered_at` | TIMESTAMP | 0 | 0.0% | 98,248 | 2016-10-07 18:32:28, 2016-10-11 14:31:29, 2016-10-16 03:20:17 |
| `has_comment` | BOOLEAN | 0 | 0.0% | 2 | False, True |

## `stg.customers`

- **Grain**: 1 row = 1 per-order customer record
- **Key**: `customer_id`
- **Rows**: 99,441

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `customer_id` | VARCHAR | 0 | 0.0% | 99,441 | 00012a2ce6f8dcda20d059ce98…, 000161a058600d5901f007fab4…, 0001fd6190edaaf884bcaf3d49… |
| `customer_unique_id` | VARCHAR | 0 | 0.0% | 96,096 | 0000366f3b9a7992bf8c76cfdf…, 0000b849f77a49e4a4ce2b2a4c…, 0000f46a3911fa3c0805444483… |
| `customer_zip_prefix` | VARCHAR | 0 | 0.0% | 14,994 | 01003, 01004, 01005 |
| `customer_city` | VARCHAR | 0 | 0.0% | 4,119 | abadia dos dourados, abadiania, abaete |
| `customer_state` | VARCHAR | 0 | 0.0% | 27 | AC, AL, AM |

## `stg.sellers`

- **Grain**: 1 row = 1 seller
- **Key**: `seller_id`
- **Rows**: 3,095

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `seller_id` | VARCHAR | 0 | 0.0% | 3,095 | 0015a82c2db000af6aaaf3ae2e…, 001cca7ae9ae17fb1caed9dfb1…, 001e6ad469a905060d959994f1… |
| `seller_zip_prefix` | VARCHAR | 0 | 0.0% | 2,246 | 01001, 01021, 01022 |
| `seller_city` | VARCHAR | 0 | 0.0% | 611 | 04482255, abadia de goias, afonso claudio |
| `seller_state` | VARCHAR | 0 | 0.0% | 23 | AC, AM, BA |

## `stg.products`

- **Grain**: 1 row = 1 product
- **Key**: `product_id`
- **Rows**: 32,951

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `product_id` | VARCHAR | 0 | 0.0% | 32,951 | 00066f42aeeb9f3007548bb9d3…, 00088930e925c41fd95ebfe695…, 0009406fd7479715e4bef61dd9… |
| `category_pt` | VARCHAR | 610 | 1.9% | 73 | agro_industria_e_comercio, alimentos, alimentos_bebidas |
| `name_length` | INTEGER | 610 | 1.9% | 66 | 5, 6, 7 |
| `description_length` | INTEGER | 610 | 1.9% | 2,960 | 4, 8, 15 |
| `photos_qty` | INTEGER | 610 | 1.9% | 19 | 1, 2, 3 |
| `weight_g` | INTEGER | 2 | 0.0% | 2,204 | 0, 2, 25 |
| `length_cm` | INTEGER | 2 | 0.0% | 99 | 7, 8, 9 |
| `height_cm` | INTEGER | 2 | 0.0% | 102 | 2, 3, 4 |
| `width_cm` | INTEGER | 2 | 0.0% | 95 | 6, 7, 8 |

## `stg.category_translation`

- **Grain**: 1 row = 1 category name
- **Key**: `category_pt`
- **Rows**: 71

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `category_pt` | VARCHAR | 0 | 0.0% | 71 | agro_industria_e_comercio, alimentos, alimentos_bebidas |
| `category_en` | VARCHAR | 0 | 0.0% | 71 | agro_industry_and_commerce, air_conditioning, art |

## `stg.geolocation`

- **Grain**: 1 row = 1 zip prefix (deduplicated)
- **Key**: `zip_prefix`
- **Rows**: 19,015

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `zip_prefix` | VARCHAR | 0 | 0.0% | 19,015 | 01001, 01002, 01003 |
| `lat` | DOUBLE | 0 | 0.0% | 18,991 | -33.690971840060584, -33.52580018289036, -33.52197132824981 |
| `lng` | DOUBLE | 0 | 0.0% | 18,990 | -72.90944364828704, -72.78282349999996, -72.74327177966269 |
| `city` | VARCHAR | 0 | 0.0% | 5,829 | abadia de goias, abadia dos dourados, abadiania |
| `state` | VARCHAR | 0 | 0.0% | 27 | AC, AL, AM |
| `source_points` | BIGINT | 0 | 0.0% | 483 | 1, 2, 3 |

## Renamed columns

| staged name | source column | reason |
|---|---|---|
| `name_length` | `product_name_lenght` | source misspelling |
| `description_length` | `product_description_lenght` | source misspelling |
| `item_price` | `price` | disambiguates item value from payment value |
| `purchased_at` … `estimated_delivery_at` | `order_*_timestamp` / `order_*_date` | consistent `_at` suffix for timestamps |
| `customer_zip_prefix` | `customer_zip_code_prefix` | brevity; kept as text to preserve leading zeros |
