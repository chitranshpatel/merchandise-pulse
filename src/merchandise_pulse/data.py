from __future__ import annotations

from pathlib import Path

import pandas as pd


TABLES = (
    "dim_date",
    "dim_supplier",
    "dim_product",
    "dim_store",
    "dim_promotion",
    "bridge_promotion_products",
    "fact_sales_weekly",
    "fact_inventory_weekly",
    "fact_forecast_weekly",
    "fact_purchase_order_lines",
)

DATE_COLUMNS = {
    "dim_date": ["date", "week_start", "week_end"],
    "dim_product": ["launch_date"],
    "dim_store": ["open_date"],
    "dim_promotion": ["start_date", "end_date"],
    "fact_sales_weekly": ["week_start"],
    "fact_inventory_weekly": ["week_start"],
    "fact_forecast_weekly": ["week_start", "forecast_created_date"],
    "fact_purchase_order_lines": [
        "order_date", "expected_delivery_date", "actual_delivery_date"
    ],
}


def load_tables(data_dir: str | Path = "data/generated") -> dict[str, pd.DataFrame]:
    data_dir = Path(data_dir)
    missing = [name for name in TABLES if not (data_dir / f"{name}.csv").exists()]
    if missing:
        names = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing generated tables: {names}. Run python scripts/generate_data.py first."
        )

    tables = {}
    for name in TABLES:
        tables[name] = pd.read_csv(
            data_dir / f"{name}.csv",
            parse_dates=DATE_COLUMNS.get(name),
        )
    return tables


def enrich_sales(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sales = tables["fact_sales_weekly"].merge(
        tables["dim_product"], on="product_id", how="left", validate="many_to_one"
    )
    sales = sales.merge(
        tables["dim_store"], on="store_id", how="left", validate="many_to_one"
    )
    suppliers = tables["dim_supplier"][["supplier_id", "supplier_name", "supplier_tier"]]
    return sales.merge(suppliers, on="supplier_id", how="left", validate="many_to_one")


def filter_frame(frame: pd.DataFrame, filters: dict[str, object] | None = None) -> pd.DataFrame:
    if not filters:
        return frame
    result = frame
    for column, selected in filters.items():
        if selected is None or column not in result:
            continue
        values = selected if isinstance(selected, (list, tuple, set)) else [selected]
        if values:
            result = result[result[column].isin(values)]
    return result


def load_quarantine_log(data_dir: str | Path = "data/generated") -> pd.DataFrame:
    path = Path(data_dir) / "quarantine_log.csv"
    if not path.exists():
        return pd.DataFrame(columns=[
            "issue_id", "source_table", "record_key", "rule", "detected_date", "status"
        ])
    return pd.read_csv(path, parse_dates=["detected_date"])
