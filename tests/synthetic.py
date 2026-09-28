"""SYNTHETIC DATA. Not Olist. Not real. Test fixture only.

Every value in this module is fabricated. It exists so continuous integration
can exercise the real SQL pipeline without the licensed dataset, which cannot be
committed to a public repository.

The fixture is deliberately small and deliberately *nasty*: it reproduces each
defect shape found in the real source, so the pipeline's handling of those cases
is exercised on every CI run rather than only when someone has the real data:

  - an order fulfilled by two sellers          (review attribution must not split)
  - an order with two reviews                  (collapse rule must fire)
  - a review_id shared by two orders           (review_id is not a primary key)
  - an order split across two payment methods  (payments must not fan out)
  - a cancelled order with no items            (must not reach the AOV denominator)
  - an order marked delivered with no date     (must not reach delay KPIs)
  - a zip prefix with a leading zero           (must survive as text)
  - a repeat customer                          (customer_unique_id vs customer_id)
  - a genuinely late order and an early one    (both sides of is_late)

Numbers here are chosen to be easy to verify by hand, not to look realistic.
No conclusion about Olist may be drawn from anything in this file.
"""

from __future__ import annotations

import csv
from pathlib import Path

SYNTHETIC_BANNER = "SYNTHETIC TEST DATA - NOT REAL OLIST DATA"

# --- customers -------------------------------------------------------------
# c-repeat-a and c-repeat-b are the SAME person (person-1) on two orders.
CUSTOMERS = [
    # customer_id, customer_unique_id, zip, city, state
    ("c-repeat-a", "person-1", "01037", "sao paulo", "SP"),
    ("c-repeat-b", "person-1", "01037", "sao paulo", "SP"),
    ("c-2", "person-2", "20040", "rio de janeiro", "RJ"),
    ("c-3", "person-3", "20040", "rio de janeiro", "RJ"),
    ("c-4", "person-4", "57020", "maceio", "AL"),
    ("c-5", "person-5", "01037", "sao paulo", "SP"),
    ("c-6", "person-6", "30110", "belo horizonte", "MG"),
]

# --- orders ----------------------------------------------------------------
# o-1  delivered early, single seller, one review
# o-2  delivered LATE, two reviews (collapse rule must pick the later one)
# o-3  delivered LATE, two sellers (seller attribution must be withheld)
# o-4  cancelled, no items at all
# o-5  delivered but NO delivery timestamp (contradiction; excluded from delay)
# o-6  delivered on the promised day exactly (boundary: on time, not late)
# o-7  repeat purchase by person-1, split across two payment methods
ORDERS = [
    # order_id, customer_id, status, purchased, approved, carrier, delivered, estimated
    ("o-1", "c-repeat-a", "delivered", "2017-05-02 10:00:00", "2017-05-02 11:00:00",
     "2017-05-04 09:00:00", "2017-05-10 15:00:00", "2017-05-20 00:00:00"),
    ("o-2", "c-2", "delivered", "2017-06-01 10:00:00", "2017-06-01 11:00:00",
     "2017-06-03 09:00:00", "2017-06-30 15:00:00", "2017-06-20 00:00:00"),
    ("o-3", "c-3", "delivered", "2017-07-01 10:00:00", "2017-07-01 11:00:00",
     "2017-07-03 09:00:00", "2017-07-25 15:00:00", "2017-07-18 00:00:00"),
    ("o-4", "c-4", "canceled", "2017-08-01 10:00:00", "", "", "", "2017-08-20 00:00:00"),
    ("o-5", "c-5", "delivered", "2017-09-01 10:00:00", "2017-09-01 11:00:00",
     "2017-09-03 09:00:00", "", "2017-09-20 00:00:00"),
    ("o-6", "c-6", "delivered", "2017-10-01 10:00:00", "2017-10-01 11:00:00",
     "2017-10-03 09:00:00", "2017-10-20 18:00:00", "2017-10-20 00:00:00"),
    ("o-7", "c-repeat-b", "delivered", "2017-06-15 10:00:00", "2017-06-15 11:00:00",
     "2017-06-17 09:00:00", "2017-06-25 15:00:00", "2017-07-05 00:00:00"),
]

# --- order items -----------------------------------------------------------
# Totals chosen to be checkable by hand:
#   item price total   = 100 + 50 + 25 + 200 + 300 + 10 + 15 = 600.00
#   freight total      =  10 +  5 +  5 +  20 +  30 +  1 +  4 =  75.00
# o-4 appears nowhere here: a cancelled order with no items.
ORDER_ITEMS = [
    # order_id, item_id, product_id, seller_id, shipping_limit, price, freight
    ("o-1", "1", "p-1", "s-1", "2017-05-05 00:00:00", "100.00", "10.00"),
    ("o-2", "1", "p-2", "s-1", "2017-06-05 00:00:00", "50.00", "5.00"),
    ("o-2", "2", "p-3", "s-1", "2017-06-05 00:00:00", "25.00", "5.00"),
    ("o-3", "1", "p-1", "s-1", "2017-07-05 00:00:00", "200.00", "20.00"),
    ("o-3", "2", "p-4", "s-2", "2017-07-05 00:00:00", "300.00", "30.00"),
    ("o-5", "1", "p-2", "s-2", "2017-09-05 00:00:00", "10.00", "1.00"),
    ("o-6", "1", "p-3", "s-1", "2017-10-05 00:00:00", "15.00", "4.00"),
    ("o-7", "1", "p-1", "s-1", "2017-06-20 00:00:00", "0.00", "0.00"),
]
# o-7 carries a zero-price line so the "item price <= 0" business rule has
# something to find; the expected totals above exclude it.

# --- payments --------------------------------------------------------------
# o-7 is split across two instruments, which is the payment fan-out case.
ORDER_PAYMENTS = [
    # order_id, sequential, type, installments, value
    ("o-1", "1", "credit_card", "3", "110.00"),
    ("o-2", "1", "boleto", "1", "85.00"),
    ("o-3", "1", "credit_card", "6", "550.00"),
    ("o-4", "1", "credit_card", "1", "0.00"),
    ("o-5", "1", "debit_card", "1", "11.00"),
    ("o-6", "1", "voucher", "1", "19.00"),
    ("o-7", "1", "voucher", "1", "5.00"),
    ("o-7", "2", "credit_card", "2", "20.00"),
]

# --- reviews ---------------------------------------------------------------
# o-2 has TWO reviews with different scores (collapse must keep the later, 1).
# rev-shared is one review_id attached to two different orders, which is why
# review_id cannot be the primary key.
ORDER_REVIEWS = [
    # review_id, order_id, score, title, message, created, answered
    ("rev-1", "o-1", "5", "", "", "2017-05-11 00:00:00", "2017-05-12 09:00:00"),
    ("rev-2a", "o-2", "3", "", "first impression", "2017-07-01 00:00:00", "2017-07-02 09:00:00"),
    ("rev-2b", "o-2", "1", "", "after support call", "2017-07-05 00:00:00", "2017-07-06 09:00:00"),
    ("rev-3", "o-3", "2", "", "late and incomplete", "2017-07-26 00:00:00", "2017-07-27 09:00:00"),
    ("rev-shared", "o-6", "4", "", "", "2017-10-21 00:00:00", "2017-10-22 09:00:00"),
    ("rev-shared", "o-7", "4", "", "", "2017-10-21 00:00:00", "2017-10-22 09:00:00"),
]

PRODUCTS = [
    # product_id, category, name_len, desc_len, photos, weight, length, height, width
    ("p-1", "cama_mesa_banho", "40", "300", "2", "900", "20", "10", "15"),
    ("p-2", "beleza_saude", "35", "250", "1", "300", "15", "8", "10"),
    ("p-3", "", "30", "200", "1", "150", "10", "5", "8"),          # no category
    ("p-4", "categoria_sem_traducao", "45", "400", "3", "5000", "60", "40", "30"),  # untranslated
]

SELLERS = [
    ("s-1", "01037", "sao paulo", "SP"),
    ("s-2", "20040", "rio de janeiro", "RJ"),
]

GEOLOCATION = [
    # Several points per prefix, so the deduplication in staging has work to do.
    ("01037", "-23.5451", "-46.6390", "sao paulo", "SP"),
    ("01037", "-23.5460", "-46.6395", "sao paulo", "SP"),
    ("01037", "-23.5440", "-46.6380", "sao paulo", "SP"),
    ("20040", "-22.9068", "-43.1729", "rio de janeiro", "RJ"),
    ("20040", "-22.9070", "-43.1730", "rio de janeiro", "RJ"),
    ("57020", "-9.6658", "-35.7353", "maceio", "AL"),
    ("30110", "-19.9167", "-43.9345", "belo horizonte", "MG"),
]

CATEGORY_TRANSLATION = [
    ("cama_mesa_banho", "bed_bath_table"),
    ("beleza_saude", "health_beauty"),
]

FILES: dict[str, tuple[list[str], list[tuple]]] = {
    "olist_customers_dataset.csv": (
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
         "customer_city", "customer_state"], CUSTOMERS),
    "olist_orders_dataset.csv": (
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
         "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"], ORDERS),
    "olist_order_items_dataset.csv": (
        ["order_id", "order_item_id", "product_id", "seller_id",
         "shipping_limit_date", "price", "freight_value"], ORDER_ITEMS),
    "olist_order_payments_dataset.csv": (
        ["order_id", "payment_sequential", "payment_type",
         "payment_installments", "payment_value"], ORDER_PAYMENTS),
    "olist_order_reviews_dataset.csv": (
        ["review_id", "order_id", "review_score", "review_comment_title",
         "review_comment_message", "review_creation_date",
         "review_answer_timestamp"], ORDER_REVIEWS),
    "olist_products_dataset.csv": (
        ["product_id", "product_category_name", "product_name_lenght",
         "product_description_lenght", "product_photos_qty", "product_weight_g",
         "product_length_cm", "product_height_cm", "product_width_cm"], PRODUCTS),
    "olist_sellers_dataset.csv": (
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"], SELLERS),
    "olist_geolocation_dataset.csv": (
        ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
         "geolocation_city", "geolocation_state"], GEOLOCATION),
    "product_category_name_translation.csv": (
        ["product_category_name", "product_category_name_english"], CATEGORY_TRANSLATION),
}

# Hand-computed expectations, so a failure points at the pipeline rather than
# sending anyone back to recompute the fixture.
EXPECTED = {
    "orders": len(ORDERS),                    # 7
    "order_items": len(ORDER_ITEMS),          # 8
    "order_payments": len(ORDER_PAYMENTS),    # 8
    "order_reviews": len(ORDER_REVIEWS),      # 6
    "customers": len(CUSTOMERS),              # 7
    "items_value": 700.00,                    # includes the 0.00 line on o-7
    "freight_value": 75.00,
    "payments_value": 800.00,
    "distinct_people": 6,                     # 7 customer_id values, 6 people
    "orders_with_items": 6,                   # o-4 has none
    "zip_prefixes": 4,                        # 7 geolocation points collapse to 4
}


def write_fixture(target_dir: Path) -> Path:
    """Write the nine synthetic CSVs into `target_dir`. Returns that directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename, (header, rows) in FILES.items():
        with (target_dir / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
    (target_dir / "README.txt").write_text(
        SYNTHETIC_BANNER + "\n\nGenerated by tests/synthetic.py for CI. "
        "Contains no Olist data and supports no conclusion about it.\n",
        encoding="utf-8",
    )
    return target_dir
