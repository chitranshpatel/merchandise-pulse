"""Generate the synthetic retail data used by Merchandise Pulse."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


SEED = 42
START_WEEK = date(2025, 2, 10)
WEEKS = 78
STATES = ["VIC", "NSW", "QLD", "SA", "WA"]
CATEGORIES = {
    "Skincare": ["Cleansers", "Serums", "Sun Care"],
    "Cosmetics": ["Face", "Eyes", "Lips"],
    "Vitamins & Supplements": ["Immunity", "Sleep", "General Health"],
    "Haircare": ["Shampoo", "Treatment", "Styling"],
    "Personal Care": ["Body Care", "Oral Care", "Deodorant"],
    "Wellness": ["Hydration", "Stress Support", "Fitness"],
    "Pharmacy Essentials": ["Pain Relief", "First Aid", "Allergy"],
}
CATEGORY_SEASON = {
    "Skincare": {12: 1.30, 1: 1.25, 2: 1.15},
    "Personal Care": {12: 1.18, 1: 1.15},
    "Vitamins & Supplements": {6: 1.30, 7: 1.35, 8: 1.22},
    "Pharmacy Essentials": {6: 1.18, 7: 1.25, 8: 1.18},
}


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def monday_weeks() -> list[date]:
    return [START_WEEK + timedelta(weeks=i) for i in range(WEEKS)]


def build_dates(weeks: list[date]) -> list[dict]:
    first = weeks[0]
    last = weeks[-1] + timedelta(days=6)
    rows = []
    current = first
    while current <= last:
        month = current.month
        season = (
            "Summer" if month in (12, 1, 2) else
            "Autumn" if month in (3, 4, 5) else
            "Winter" if month in (6, 7, 8) else "Spring"
        )
        week_start = current - timedelta(days=current.weekday())
        rows.append({
            "date": current.isoformat(),
            "week_start": week_start.isoformat(),
            "week_end": (week_start + timedelta(days=6)).isoformat(),
            "year": current.year,
            "quarter": f"Q{(month - 1) // 3 + 1}",
            "month_number": month,
            "month_name": current.strftime("%B"),
            "week_of_year": current.isocalendar().week,
            "season": season,
        })
        current += timedelta(days=1)
    return rows


def build_suppliers() -> list[dict]:
    names = [
        "Northstar Health", "Luma Beauty", "Harbour Labs", "Everwell",
        "Juniper Care", "Kindred Wellness", "Solace Skin", "Brightside",
        "Field & Form", "Common Good", "Aster Health", "Morrow Beauty",
    ]
    categories = list(CATEGORIES)
    rows = []
    for i, name in enumerate(names, start=1):
        rows.append({
            "supplier_id": f"SUP{i:03d}",
            "supplier_name": name,
            "supplier_tier": "Strategic" if i <= 4 else "Core" if i <= 9 else "Emerging",
            "primary_category": categories[(i - 1) % len(categories)],
            "standard_lead_time_days": 7 + (i % 4) * 3,
            "otif_target": f"{0.96 if i <= 4 else 0.94:.2f}",
            "active_flag": True,
        })
    return rows


def build_products(rng: random.Random, suppliers: list[dict]) -> list[dict]:
    category_names = list(CATEGORIES)
    adjectives = ["Daily", "Calm", "Pure", "Active", "Fresh", "Restore", "Essential", "Glow"]
    nouns = ["Blend", "Care", "Formula", "Therapy", "Boost", "Complex", "Ritual", "Solution"]
    rows = []
    for i in range(1, 97):
        category = category_names[(i - 1) % len(category_names)]
        subcategory = CATEGORIES[category][(i - 1) % 3]
        supplier = suppliers[(i * 5 + category_names.index(category)) % len(suppliers)]
        cost = round(rng.uniform(3.5, 28.0), 2)
        margin = rng.uniform(0.34, 0.57)
        price = round(cost / (1 - margin), 2)
        launch_offset = rng.randint(0, 18)
        rows.append({
            "product_id": f"SKU{i:04d}",
            "product_name": f"{adjectives[i % len(adjectives)]} {subcategory} {nouns[(i * 3) % len(nouns)]}",
            "brand": f"{supplier['supplier_name'].split()[0]} {['Essentials', 'Collective'][i % 2]}",
            "category": category,
            "subcategory": subcategory,
            "supplier_id": supplier["supplier_id"],
            "unit_cost": f"{cost:.2f}",
            "regular_unit_price": f"{price:.2f}",
            "launch_date": (START_WEEK + timedelta(weeks=launch_offset)).isoformat(),
            "private_label_flag": i % 9 == 0,
            "active_flag": True,
        })
    return rows


def build_stores() -> list[dict]:
    rows = []
    for i in range(1, 25):
        channel = "Digital" if i > 22 else "Beauty Retail" if i > 15 else "Pharmacy Retail"
        state = STATES[(i - 1) % len(STATES)]
        size = ["Small", "Medium", "Large"][(i - 1) % 3]
        rows.append({
            "store_id": f"STR{i:03d}",
            "store_name": f"{state} {channel.split()[0]} {i:02d}",
            "channel": channel,
            "store_format": "Online Fulfilment" if channel == "Digital" else f"{size} Format",
            "state": state,
            "region": f"{state} Region {(i - 1) % 2 + 1}",
            "size_band": size,
            "open_date": (START_WEEK - timedelta(weeks=52 + i)).isoformat(),
            "active_flag": True,
        })
    return rows


def build_ranging(rng: random.Random, stores: list[dict], products: list[dict]) -> set[tuple[str, str]]:
    ranged = set()
    for store in stores:
        for product in products:
            channel = store["channel"]
            category = product["category"]
            base = 0.72 if store["size_band"] == "Large" else 0.57 if store["size_band"] == "Medium" else 0.43
            if channel == "Beauty Retail" and category in ("Skincare", "Cosmetics", "Haircare"):
                base += 0.22
            if channel == "Pharmacy Retail" and category in ("Vitamins & Supplements", "Pharmacy Essentials"):
                base += 0.20
            if channel == "Digital":
                base = 0.92
            if rng.random() < min(base, 0.98):
                ranged.add((store["store_id"], product["product_id"]))
    return ranged


def build_promotions(rng: random.Random, weeks: list[date], products: list[dict]) -> tuple[list[dict], list[dict], dict]:
    promotions = []
    bridge = []
    lookup = {}
    for i in range(1, 43):
        start_index = 10 + ((i * 7) % (WEEKS - 14))
        duration = 1 if i % 3 else 2
        start = weeks[start_index]
        end = start + timedelta(days=7 * duration - 1)
        channel = ["Pharmacy Retail", "Beauty Retail", "Digital"][i % 3]
        selected = rng.sample(products, 3 + i % 4)
        funding = round(400 + i * 37 + rng.uniform(0, 500), 2)
        promotion_id = f"PRM{i:03d}"
        promotions.append({
            "promotion_id": promotion_id,
            "promotion_name": f"Campaign {i:02d}",
            "promotion_type": ["Percentage", "Multibuy", "Catalogue", "Launch"][i % 4],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "channel": channel,
            "supplier_funding_total": f"{funding:.2f}",
            "status": "Complete",
        })
        weights = [rng.random() for _ in selected]
        allocations = [round(funding * w / sum(weights), 2) for w in weights]
        allocations[-1] = round(funding - sum(allocations[:-1]), 2)
        discount = 0.18 + (i % 4) * 0.05
        for product, allocation in zip(selected, allocations):
            price = float(product["regular_unit_price"])
            bridge.append({
                "promotion_id": promotion_id,
                "product_id": product["product_id"],
                "promotional_unit_price": f"{price * (1 - discount):.2f}",
                "funding_allocation": f"{allocation:.2f}",
            })
            for week_offset in range(duration):
                lookup[(start + timedelta(weeks=week_offset), channel, product["product_id"])] = {
                    "promotion_id": promotion_id,
                    "price": round(price * (1 - discount), 2),
                    "uplift": 1.20 + (i % 5) * 0.18,
                }
    return promotions, bridge, lookup


def poisson(rng: random.Random, mean: float) -> int:
    if mean <= 0:
        return 0
    if mean > 35:
        return max(0, round(rng.gauss(mean, math.sqrt(mean))))
    limit = math.exp(-mean)
    product = 1.0
    count = 0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def build_weekly_facts(
    rng: random.Random,
    weeks: list[date],
    stores: list[dict],
    products: list[dict],
    ranged: set[tuple[str, str]],
    promo_lookup: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    sales = []
    inventory = []
    forecasts = []
    stock = defaultdict(lambda: 18)
    product_map = {p["product_id"]: p for p in products}

    for store in stores:
        store_factor = {"Small": 0.75, "Medium": 1.0, "Large": 1.35}[store["size_band"]]
        if store["channel"] == "Digital":
            store_factor = 1.65
        for product in products:
            key = (store["store_id"], product["product_id"])
            if key not in ranged:
                continue
            launch = date.fromisoformat(product["launch_date"])
            base = rng.uniform(3.5, 14.0) * store_factor
            cost = float(product["unit_cost"])
            regular_price = float(product["regular_unit_price"])
            opening = rng.randint(12, 35)
            stock[key] = opening

            for week_index, week in enumerate(weeks):
                if week < launch:
                    continue
                season = CATEGORY_SEASON.get(product["category"], {}).get(week.month, 1.0)
                trend = 1 + week_index * 0.0015
                demand_mean = base * season * trend

                # A new beauty range works in large stores but struggles in small ones.
                if product["product_id"] in {f"SKU{i:04d}" for i in range(85, 97)} and store["channel"] == "Beauty Retail":
                    demand_mean *= 1.45 if store["size_band"] == "Large" else 0.62

                promo = promo_lookup.get((week, store["channel"], product["product_id"]))
                if promo:
                    demand_mean *= promo["uplift"]
                demand = poisson(rng, demand_mean)

                supplier_id = product_map[product["product_id"]]["supplier_id"]
                service_factor = 1.0
                if supplier_id == "SUP001" and week_index >= WEEKS - 8:
                    service_factor = 0.48
                receipts = max(0, round(demand_mean * rng.uniform(0.8, 1.35) * service_factor))
                if product["category"] == "Cosmetics" and week_index >= WEEKS - 12:
                    receipts = round(receipts * 1.55)
                available = opening + receipts
                units = min(demand, available)
                closing = available - units
                shortage = max(0, demand - available)
                in_stock_days = 7 if shortage == 0 else max(0, round(7 * available / max(demand, 1)))
                selling_price = promo["price"] if promo else regular_price
                gross_sales = round(units * regular_price, 2)
                net_sales = round(units * selling_price, 2)
                discount = round(gross_sales - net_sales, 2)

                sales.append({
                    "week_start": week.isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                    "promotion_id": promo["promotion_id"] if promo else "",
                    "units_sold": units,
                    "gross_sales": f"{gross_sales:.2f}",
                    "discount_value": f"{discount:.2f}",
                    "net_sales": f"{net_sales:.2f}",
                    "cost_of_goods": f"{units * cost:.2f}",
                    "returns_units": 1 if units > 20 and rng.random() < 0.08 else 0,
                })
                inventory.append({
                    "week_start": week.isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                    "opening_stock_units": opening,
                    "receipts_units": receipts,
                    "closing_stock_units": closing,
                    "in_stock_days": in_stock_days,
                    "ranged_flag": True,
                })

                bias = 1.18 if product["category"] == "Cosmetics" else 0.84 if product["category"] == "Vitamins & Supplements" else 1.0
                forecast = max(0, round(demand_mean * bias * rng.uniform(0.82, 1.18)))
                forecasts.append({
                    "week_start": week.isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                    "forecast_version": "LAG_4W",
                    "forecast_created_date": (week - timedelta(weeks=4)).isoformat(),
                    "forecast_units": forecast,
                })
                opening = closing
    return sales, inventory, forecasts


def build_purchase_orders(
    rng: random.Random,
    weeks: list[date],
    stores: list[dict],
    products: list[dict],
) -> list[dict]:
    rows = []
    event_number = 1
    line_number = 1
    for week_index, week in enumerate(weeks[2:], start=2):
        for product_index, product in enumerate(products):
            if (product_index + week_index) % 3:
                continue
            supplier = product["supplier_id"]
            destination = stores[(line_number * 7) % len(stores)]["store_id"]
            ordered = rng.randint(24, 140)
            order_date = week - timedelta(days=10)
            expected = week
            late_chance = 0.08
            short_chance = 0.07
            if supplier == "SUP001" and week_index >= WEEKS - 8:
                late_chance = 0.58
                short_chance = 0.38
            elif supplier == "SUP003":
                late_chance = 0.04
                short_chance = 0.03
            late = rng.random() < late_chance
            short = rng.random() < short_chance
            received = round(ordered * rng.uniform(0.68, 0.94)) if short else ordered
            actual = expected + timedelta(days=rng.randint(1, 5)) if late else expected - timedelta(days=rng.randint(0, 2))
            po_line_id = f"POL{line_number:06d}"
            purchase_order_id = f"PO{(line_number - 1) // 5 + 1:05d}"

            split = received > 50 and rng.random() < 0.18
            quantities = [received]
            dates = [actual]
            if split:
                first = round(received * rng.uniform(0.45, 0.75))
                quantities = [first, received - first]
                dates = [actual - timedelta(days=1), actual]
            for quantity, delivery_date in zip(quantities, dates):
                rows.append({
                    "delivery_event_id": f"DEV{event_number:07d}",
                    "po_line_id": po_line_id,
                    "purchase_order_id": purchase_order_id,
                    "supplier_id": supplier,
                    "product_id": product["product_id"],
                    "destination_store_id": destination,
                    "order_date": order_date.isoformat(),
                    "expected_delivery_date": expected.isoformat(),
                    "actual_delivery_date": delivery_date.isoformat(),
                    "ordered_units": ordered,
                    "received_units": quantity,
                    "line_status": "Complete" if received >= ordered else "Partially Received",
                })
                event_number += 1
            line_number += 1
    return rows


def build_quarantine_log(weeks: list[date]) -> list[dict]:
    detected = (weeks[-1] + timedelta(days=1)).isoformat()
    return [
        {"issue_id": "DQ001", "source_table": "sales_staging", "record_key": "STR004|SKU0021|2026-07-20", "rule": "Duplicate business key", "detected_date": detected, "status": "Quarantined"},
        {"issue_id": "DQ002", "source_table": "sales_staging", "record_key": "STR011|SKU0044|2026-07-27", "rule": "Duplicate business key", "detected_date": detected, "status": "Quarantined"},
        {"issue_id": "DQ003", "source_table": "product_staging", "record_key": "SKU0097", "rule": "Missing supplier mapping", "detected_date": detected, "status": "Quarantined"},
        {"issue_id": "DQ004", "source_table": "inventory_staging", "record_key": "STR008|SKU0032|2026-08-03", "rule": "Negative closing stock", "detected_date": detected, "status": "Quarantined"},
        {"issue_id": "DQ005", "source_table": "purchase_order_staging", "record_key": "POL009812", "rule": "Receipt date before order date", "detected_date": detected, "status": "Quarantined"},
        {"issue_id": "DQ006", "source_table": "promotion_staging", "record_key": "PRM043", "rule": "End date before start date", "detected_date": detected, "status": "Quarantined"},
        {"issue_id": "DQ007", "source_table": "forecast_staging", "record_key": "STR019|SKU0014|2026-08-03", "rule": "Missing forecast units", "detected_date": detected, "status": "Quarantined"},
    ]


def validate(
    tables: dict[str, list[dict]],
    scenario: dict,
) -> dict:
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    key_specs = {
        "dim_supplier": ("supplier_id",),
        "dim_product": ("product_id",),
        "dim_store": ("store_id",),
        "dim_promotion": ("promotion_id",),
        "bridge_promotion_products": ("promotion_id", "product_id"),
        "fact_sales_weekly": ("week_start", "store_id", "product_id"),
        "fact_inventory_weekly": ("week_start", "store_id", "product_id"),
        "fact_forecast_weekly": ("week_start", "store_id", "product_id", "forecast_version"),
        "fact_purchase_order_lines": ("delivery_event_id",),
    }
    for table, keys in key_specs.items():
        seen = set()
        duplicates = 0
        for row in tables[table]:
            key = tuple(row[column] for column in keys)
            if key in seen:
                duplicates += 1
            seen.add(key)
        add(f"{table}: unique grain", duplicates == 0, f"{duplicates} duplicate keys")

    products = {row["product_id"] for row in tables["dim_product"]}
    stores = {row["store_id"] for row in tables["dim_store"]}
    suppliers = {row["supplier_id"] for row in tables["dim_supplier"]}
    bad_sales_keys = sum(
        row["product_id"] not in products or row["store_id"] not in stores
        for row in tables["fact_sales_weekly"]
    )
    add("sales foreign keys", bad_sales_keys == 0, f"{bad_sales_keys} invalid mappings")

    bad_math = sum(
        abs(float(row["gross_sales"]) - float(row["discount_value"]) - float(row["net_sales"])) > 0.011
        for row in tables["fact_sales_weekly"]
    )
    add("sales arithmetic", bad_math == 0, f"{bad_math} rows failed")

    bad_days = sum(not 0 <= int(row["in_stock_days"]) <= 7 for row in tables["fact_inventory_weekly"])
    add("inventory in-stock days", bad_days == 0, f"{bad_days} invalid rows")

    bad_po_keys = sum(
        row["supplier_id"] not in suppliers or row["product_id"] not in products or row["destination_store_id"] not in stores
        for row in tables["fact_purchase_order_lines"]
    )
    add("purchase-order foreign keys", bad_po_keys == 0, f"{bad_po_keys} invalid mappings")

    funding_by_promo = defaultdict(float)
    for row in tables["bridge_promotion_products"]:
        funding_by_promo[row["promotion_id"]] += float(row["funding_allocation"])
    promo_total = {row["promotion_id"]: float(row["supplier_funding_total"]) for row in tables["dim_promotion"]}
    bad_funding = sum(abs(funding_by_promo[promo] - total) > 0.011 for promo, total in promo_total.items())
    add("promotion funding reconciliation", bad_funding == 0, f"{bad_funding} campaigns failed")

    add("scenario: late supplier decline", scenario["supplier_1_recent_otif"] < scenario["supplier_1_prior_otif"],
        f"SUP001 recent {scenario['supplier_1_recent_otif']:.1%}, prior {scenario['supplier_1_prior_otif']:.1%}")
    add("scenario: category forecast bias", scenario["cosmetics_bias"] > 0.08 and scenario["vitamins_bias"] < -0.08,
        f"Cosmetics {scenario['cosmetics_bias']:.1%}, Vitamins {scenario['vitamins_bias']:.1%}")
    add("dataset size", len(tables["fact_sales_weekly"]) >= 75_000,
        f"{len(tables['fact_sales_weekly']):,} weekly sales rows")

    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "row_counts": {name: len(rows) for name, rows in tables.items()},
        "scenario_metrics": scenario,
    }


def scenario_metrics(tables: dict[str, list[dict]], weeks: list[date]) -> dict:
    products = {row["product_id"]: row for row in tables["dim_product"]}
    line_events = defaultdict(list)
    for row in tables["fact_purchase_order_lines"]:
        line_events[row["po_line_id"]].append(row)

    def otif(lines: list[list[dict]]) -> float:
        results = []
        for events in lines:
            ordered = int(events[0]["ordered_units"])
            received = sum(int(event["received_units"]) for event in events)
            final_date = max(date.fromisoformat(event["actual_delivery_date"]) for event in events)
            expected = date.fromisoformat(events[0]["expected_delivery_date"])
            results.append(received >= ordered and final_date <= expected)
        return sum(results) / len(results) if results else 0.0

    cutoff = weeks[-8]
    sup1 = [events for events in line_events.values() if events[0]["supplier_id"] == "SUP001"]
    recent = [events for events in sup1 if date.fromisoformat(events[0]["expected_delivery_date"]) >= cutoff]
    prior = [events for events in sup1 if date.fromisoformat(events[0]["expected_delivery_date"]) < cutoff]

    totals = defaultdict(lambda: [0, 0])
    for row in tables["fact_forecast_weekly"]:
        category = products[row["product_id"]]["category"]
        totals[category][0] += int(row["forecast_units"])
    for row in tables["fact_sales_weekly"]:
        category = products[row["product_id"]]["category"]
        totals[category][1] += int(row["units_sold"])

    def bias(category: str) -> float:
        forecast, actual = totals[category]
        return (forecast - actual) / actual

    return {
        "supplier_1_recent_otif": round(otif(recent), 4),
        "supplier_1_prior_otif": round(otif(prior), 4),
        "cosmetics_bias": round(bias("Cosmetics"), 4),
        "vitamins_bias": round(bias("Vitamins & Supplements"), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    rng = random.Random(SEED)
    weeks = monday_weeks()
    suppliers = build_suppliers()
    products = build_products(rng, suppliers)
    stores = build_stores()
    ranged = build_ranging(rng, stores, products)
    promotions, bridge, promo_lookup = build_promotions(rng, weeks, products)
    sales, inventory, forecasts = build_weekly_facts(rng, weeks, stores, products, ranged, promo_lookup)
    purchase_orders = build_purchase_orders(rng, weeks, stores, products)

    tables = {
        "dim_date": build_dates(weeks),
        "dim_supplier": suppliers,
        "dim_product": products,
        "dim_store": stores,
        "dim_promotion": promotions,
        "bridge_promotion_products": bridge,
        "fact_sales_weekly": sales,
        "fact_inventory_weekly": inventory,
        "fact_forecast_weekly": forecasts,
        "fact_purchase_order_lines": purchase_orders,
    }
    for name, rows in tables.items():
        write_csv(args.output / f"{name}.csv", rows)
    write_csv(args.output / "quarantine_log.csv", build_quarantine_log(weeks))

    scenario = scenario_metrics(tables, weeks)
    report = validate(tables, scenario)
    (args.output / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "seed": SEED,
        "first_week": weeks[0].isoformat(),
        "last_week": weeks[-1].isoformat(),
        "row_counts": report["row_counts"],
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
