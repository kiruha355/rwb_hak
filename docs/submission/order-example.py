#!/usr/bin/env python3
"""Read one real linked Olist example; no DB, writes only an optional W-12 JSON."""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import json
from pathlib import Path

PACK = Path(__file__).resolve().parent
ROOT = PACK.parents[1]
ORDER_ID = "e481f51cbdc54678b7cc49136f2d6af7"


def rows(name: str):
    with (ROOT / "data" / name).open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def project(row, names):
    return {name: row[name] for name in names}


def total(values):
    # Source empty cell is unavailable for this display, never measured zero.
    return str(sum((Decimal(value) for value in values), Decimal("0"))) if values and all(values) else None


def example():
    order = next(row for row in rows("olist_orders_dataset.csv") if row["order_id"] == ORDER_ID)
    items = [row for row in rows("olist_order_items_dataset.csv") if row["order_id"] == ORDER_ID]
    payments = [row for row in rows("olist_order_payments_dataset.csv") if row["order_id"] == ORDER_ID]
    reviews = [row for row in rows("olist_order_reviews_dataset.csv") if row["order_id"] == ORDER_ID]
    customer = next(row for row in rows("olist_customers_dataset.csv") if row["customer_id"] == order["customer_id"])
    product_ids = {row["product_id"] for row in items}
    seller_ids = {row["seller_id"] for row in items}
    products = [row for row in rows("olist_products_dataset.csv") if row["product_id"] in product_ids]
    sellers = [row for row in rows("olist_sellers_dataset.csv") if row["seller_id"] in seller_ids]
    categories = {row["product_category_name"] for row in products}
    translations = [row for row in rows("product_category_name_translation.csv") if row["product_category_name"] in categories]
    item_gmv = [str(Decimal(row["price"]) + Decimal(row["freight_value"])) if row["price"] and row["freight_value"] else "" for row in items]
    return {
        "method": "CSV read-only; not loaded raw/core; no SQL executed",
        "order": order,
        "customer_context": customer,
        "items": items,
        "payments": payments,
        "review_pairs": [project(row, ["review_id", "order_id", "review_score", "review_creation_date", "review_answer_timestamp"]) for row in reviews],
        "products": [project(row, ["product_id", "product_category_name", "product_weight_g"]) for row in products],
        "sellers": sellers,
        "translations": translations,
        "counts": {"orders": 1, "items": len(items), "payments": len(payments), "review_pairs": len(reviews), "rows_in_naive_inner_join": len(items) * len(payments) * len(reviews)},
        "csv_amounts": {"item_price": total([row["price"] for row in items]), "freight": total([row["freight_value"] for row in items]), "order_gmv": total(item_gmv), "payment_amount": total([row["payment_value"] for row in payments])},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and not args.output.resolve().is_relative_to(PACK):
        parser.error("output must stay in docs/submission")
    result = example()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
