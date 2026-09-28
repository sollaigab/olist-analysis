# Data dictionary — staging layer

Generated from `data/olist.duckdb` on 2026-09-28 by `src/profile_columns.py`. Every figure below is the output of a query run at generation time; nothing here is transcribed by hand.

Column names are the **staged** names. Where a staged name differs from the source CSV column, the source name is given in the notes so lineage stays traceable.

## `stg.orders`

- **Grain**: 1 row = 1 order
- **Key**: `order_id`
- **Rows**: 99,441

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `order_id` | VARCHAR | 0 | 0.0% | 99,441 | e481f51cbdc54678b7cc49136f…, 82566a660a982b15fb86e904c8…, 432aaf21d85167c2c86ec9448c… |
| `customer_id` | VARCHAR | 0 | 0.0% | 99,441 | f88197465ea7920adcdbec7375…, 31ad1d1b63eb9962463f764d4e…, 3df704f53d3f1d4818840b34ec… |
| `order_status` | VARCHAR | 0 | 0.0% | 8 | approved, shipped, delivered |
| `purchased_at` | TIMESTAMP | 0 | 0.0% | 98,875 | 2017-12-26 23:41:31, 2018-03-15 08:52:40, 2018-02-20 23:46:53 |
| `approved_at` | TIMESTAMP | 160 | 0.2% | 90,733 | 2017-10-02 11:07:15, 2017-07-29 12:05:32, 2017-10-26 16:08:14 |
| `delivered_carrier_at` | TIMESTAMP | 1,783 | 1.8% | 81,018 | 2017-10-04 19:55:00, 2018-02-14 19:46:34, 2017-05-22 10:07:46 |
| `delivered_customer_at` | TIMESTAMP | 2,965 | 3.0% | 95,664 | 2017-07-26 10:57:55, 2018-03-13 23:58:43, 2018-05-21 15:22:11 |
| `estimated_delivery_at` | TIMESTAMP | 0 | 0.0% | 459 | 2018-08-13 00:00:00, 2018-03-20 00:00:00, 2017-06-12 00:00:00 |

## `stg.order_items`

- **Grain**: 1 row = 1 item line within an order
- **Key**: `(order_id, order_item_id)`
- **Rows**: 112,650

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `order_id` | VARCHAR | 0 | 0.0% | 98,666 | 00018f77f2f0320c557190d7a1…, 00119ff934e539cf26f92b9ef0…, 001b76dd48a5b1eee3e87778da… |
| `order_item_id` | INTEGER | 0 | 0.0% | 21 | 6, 10, 15 |
| `product_id` | VARCHAR | 0 | 0.0% | 32,951 | ef92defde845ab8450f9d70c52…, 8d4f2bb7e93e6710a28f34fa83…, 368c6c730842d78016ad823897… |
| `seller_id` | VARCHAR | 0 | 0.0% | 3,095 | dd7ddc04e1b6c2c614352b383e…, 5b51032eddd242adc84c38acab…, a416b6a846a11724393025641d… |
| `shipping_limit_at` | TIMESTAMP | 0 | 0.0% | 93,318 | 2018-03-21 11:10:11, 2017-03-29 13:05:42, 2017-11-30 06:30:55 |
| `item_price` | DECIMAL(12,2) | 0 | 0.0% | 5,968 | 53.99, 49.90, 99.00 |
| `freight_value` | DECIMAL(12,2) | 0 | 0.0% | 6,999 | 12.79, 26.33, 16.43 |

## `stg.order_payments`

- **Grain**: 1 row = 1 payment instrument on an order
- **Key**: `(order_id, payment_sequential)`
- **Rows**: 103,886

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `order_id` | VARCHAR | 0 | 0.0% | 99,440 | ba78997921bbcdc1373bb41e91…, 12e5cfe0e4716b59afb0e0f4a3…, c39414c195d0f94c9d9c35e7c6… |
| `payment_sequential` | INTEGER | 0 | 0.0% | 29 | 3, 11, 19 |
| `payment_type` | VARCHAR | 0 | 0.0% | 5 | boleto, voucher, debit_card |
| `payment_installments` | INTEGER | 0 | 0.0% | 24 | 15, 11, 22 |
| `payment_value` | DECIMAL(12,2) | 0 | 0.0% | 29,077 | 96.12, 98.94, 283.34 |

## `stg.order_reviews`

- **Grain**: 1 row = 1 review of 1 order
- **Key**: `(review_id, order_id)`
- **Rows**: 99,224

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `review_id` | VARCHAR | 0 | 0.0% | 98,410 | 96052551d87e5f62e6c9f6974e…, 66e4430c5bc6b7e3773886bf1c…, bf566b3910c328733baf7fca7d… |
| `order_id` | VARCHAR | 0 | 0.0% | 98,673 | b18dcdf73be66366873cd26c57…, 583174fbe37d3d5f0d6661be3a…, ae168dfba236919411fe08f336… |
| `review_score` | SMALLINT | 0 | 0.0% | 5 | 1, 2, 4 |
| `review_comment_title` | VARCHAR | 87,656 | 88.3% | 4,527 | Ótimo Produto! , Super produto , Produto pirata! |
| `review_comment_message` | VARCHAR | 58,247 | 58.7% | 36,159 | Processo de compra tranqui…, Tomara q dure pois é de pe…, Ocorreu tudo como contrata… |
| `review_created_at` | TIMESTAMP | 0 | 0.0% | 636 | 2017-12-19 00:00:00, 2018-03-24 00:00:00, 2018-07-10 00:00:00 |
| `review_answered_at` | TIMESTAMP | 0 | 0.0% | 98,248 | 2018-03-11 03:05:13, 2018-05-24 03:00:01, 2018-03-26 15:58:32 |
| `has_comment` | BOOLEAN | 0 | 0.0% | 2 | False, True |

## `stg.customers`

- **Grain**: 1 row = 1 per-order customer record
- **Key**: `customer_id`
- **Rows**: 99,441

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `customer_id` | VARCHAR | 0 | 0.0% | 99,441 | 4e7b3e00288586ebd08712fdd0…, fd826e7cf63160e536e0908c76…, a7c125a0a07b75146167b7f04a… |
| `customer_unique_id` | VARCHAR | 0 | 0.0% | 96,096 | 259dac757896d24d7702b9acbb…, 4390ddbb6276a66ff1736a6710…, 424aca6872c5bab80780a8dec0… |
| `customer_zip_prefix` | VARCHAR | 0 | 0.0% | 14,994 | 09790, 89254, 04534 |
| `customer_city` | VARCHAR | 0 | 0.0% | 4,119 | curitiba, montes claros, rio de janeiro |
| `customer_state` | VARCHAR | 0 | 0.0% | 27 | SP, MG, MA |

## `stg.sellers`

- **Grain**: 1 row = 1 seller
- **Key**: `seller_id`
- **Rows**: 3,095

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `seller_id` | VARCHAR | 0 | 0.0% | 3,095 | d1b65fc7debc3361ea86b5f14c…, c0f3eea2e14555b6faeea3dd58…, 1b938a7ec6ac5061a66a3766e0… |
| `seller_zip_prefix` | VARCHAR | 0 | 0.0% | 2,246 | 04156, 86707, 03562 |
| `seller_city` | VARCHAR | 0 | 0.0% | 611 | rio de janeiro, curitiba, itirapina |
| `seller_state` | VARCHAR | 0 | 0.0% | 23 | PE, PB, RO |

## `stg.products`

- **Grain**: 1 row = 1 product
- **Key**: `product_id`
- **Rows**: 32,951

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `product_id` | VARCHAR | 0 | 0.0% | 32,951 | 2548af3e6e77a690cf3eb6368e…, f53103a77d9cf245e579ea37e5…, c78b767da00efb70c1bcccab87… |
| `category_pt` | VARCHAR | 610 | 1.9% | 73 | perfumaria, bebes, cool_stuff |
| `name_length` | INTEGER | 610 | 1.9% | 66 | 27, 37, 60 |
| `description_length` | INTEGER | 610 | 1.9% | 2,960 | 1272, 184, 630 |
| `photos_qty` | INTEGER | 610 | 1.9% | 19 | 1, 12, 17 |
| `weight_g` | INTEGER | 2 | 0.0% | 2,204 | 1700, 8950, 6000 |
| `length_cm` | INTEGER | 2 | 0.0% | 99 | 16, 21, 42 |
| `height_cm` | INTEGER | 2 | 0.0% | 102 | 19, 7, 11 |
| `width_cm` | INTEGER | 2 | 0.0% | 95 | 20, 15, 11 |

## `stg.category_translation`

- **Grain**: 1 row = 1 category name
- **Key**: `category_pt`
- **Rows**: 71

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `category_pt` | VARCHAR | 0 | 0.0% | 71 | esporte_lazer, brinquedos, telefonia_fixa |
| `category_en` | VARCHAR | 0 | 0.0% | 71 | auto, food_drink, small_appliances |

## `stg.geolocation`

- **Grain**: 1 row = 1 zip prefix (deduplicated)
- **Key**: `zip_prefix`
- **Rows**: 19,015

| column | type | nulls | null % | distinct | sample values |
|---|---|---:|---:|---:|---|
| `zip_prefix` | VARCHAR | 0 | 0.0% | 19,015 | 26180, 26413, 27113 |
| `lat` | DOUBLE | 0 | 0.0% | 18,991 | -22.3860904684299, -22.551781145139476, -22.709328438971543 |
| `lng` | DOUBLE | 0 | 0.0% | 18,990 | -42.98416079378703, -43.52827339788494, -43.62431484673769 |
| `city` | VARCHAR | 0 | 0.0% | 5,829 | belford roxo, nilopolis, resende |
| `state` | VARCHAR | 0 | 0.0% | 27 | MG, SP, DF |
| `source_points` | BIGINT | 0 | 0.0% | 483 | 66, 31, 55 |

## Renamed columns

| staged name | source column | reason |
|---|---|---|
| `name_length` | `product_name_lenght` | source misspelling |
| `description_length` | `product_description_lenght` | source misspelling |
| `item_price` | `price` | disambiguates item value from payment value |
| `purchased_at` … `estimated_delivery_at` | `order_*_timestamp` / `order_*_date` | consistent `_at` suffix for timestamps |
| `customer_zip_prefix` | `customer_zip_code_prefix` | brevity; kept as text to preserve leading zeros |
