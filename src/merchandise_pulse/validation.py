from __future__ import annotations

import pandas as pd


def duplicate_count(frame: pd.DataFrame, keys: list[str]) -> int:
    return int(frame.duplicated(keys, keep=False).sum())


def missing_mapping_count(
    fact: pd.DataFrame, dimension: pd.DataFrame, key: str
) -> int:
    valid = set(dimension[key].dropna())
    return int((~fact[key].isin(valid)).sum())


def data_quality_score(
    duplicates: int = 0,
    missing_mappings: int = 0,
    invalid_negative_values: int = 0,
    invalid_date_sequences: int = 0,
    stale_required_table: bool = False,
) -> float:
    penalty = min(25, duplicates * 5)
    penalty += min(25, missing_mappings * 5)
    penalty += min(15, invalid_negative_values * 3)
    penalty += min(15, invalid_date_sequences * 3)
    penalty += 20 if stale_required_table else 0
    return float(max(0, 100 - penalty))


def audit_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks = []

    def add(domain: str, check: str, failures: int) -> None:
        checks.append({
            "domain": domain, "check": check, "failures": int(failures),
            "status": "Pass" if failures == 0 else "Fail",
        })

    add("Sales", "Unique weekly store–SKU grain", duplicate_count(
        tables["fact_sales_weekly"], ["week_start", "store_id", "product_id"]
    ))
    add("Inventory", "Unique weekly store–SKU grain", duplicate_count(
        tables["fact_inventory_weekly"], ["week_start", "store_id", "product_id"]
    ))
    add("Forecast", "Unique weekly version grain", duplicate_count(
        tables["fact_forecast_weekly"], ["week_start", "store_id", "product_id", "forecast_version"]
    ))
    add("Supplier", "Unique delivery events", duplicate_count(
        tables["fact_purchase_order_lines"], ["delivery_event_id"]
    ))
    add("Sales", "Valid product mappings", missing_mapping_count(
        tables["fact_sales_weekly"], tables["dim_product"], "product_id"
    ))
    add("Sales", "Valid store mappings", missing_mapping_count(
        tables["fact_sales_weekly"], tables["dim_store"], "store_id"
    ))
    arithmetic_failures = (
        (
            tables["fact_sales_weekly"]["gross_sales"]
            - tables["fact_sales_weekly"]["discount_value"]
            - tables["fact_sales_weekly"]["net_sales"]
        ).abs() > .011
    ).sum()
    add("Sales", "Gross sales less discount equals net sales", arithmetic_failures)
    add("Inventory", "In-stock days between zero and seven", (
        ~tables["fact_inventory_weekly"]["in_stock_days"].between(0, 7)
    ).sum())
    add("Inventory", "No negative closing stock", (
        tables["fact_inventory_weekly"]["closing_stock_units"] < 0
    ).sum())
    add("Supplier", "Delivery date not before order date", (
        tables["fact_purchase_order_lines"]["actual_delivery_date"]
        < tables["fact_purchase_order_lines"]["order_date"]
    ).sum())
    add("Promotion", "End date not before start date", (
        tables["dim_promotion"]["end_date"] < tables["dim_promotion"]["start_date"]
    ).sum())
    return pd.DataFrame(checks)
