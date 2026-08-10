from __future__ import annotations

import pandas as pd

from .commercial import safe_divide


def inventory_summary(inventory: pd.DataFrame) -> dict[str, float | None]:
    ranged = inventory[inventory["ranged_flag"].astype(bool)]
    possible_days = len(ranged) * 7
    availability = safe_divide(float(ranged["in_stock_days"].sum()), possible_days)
    return {
        "availability_pct": availability,
        "stockout_rate": None if availability is None else 1 - availability,
        "closing_stock_units": int(ranged["closing_stock_units"].sum()),
    }


def add_lost_sales_estimate(
    inventory: pd.DataFrame,
    sales: pd.DataFrame,
    forecasts: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    keys = ["week_start", "store_id", "product_id"]
    frame = inventory.merge(
        sales[keys + ["units_sold"]], on=keys, how="left", validate="one_to_one"
    ).merge(
        forecasts[keys + ["forecast_units"]], on=keys, how="left", validate="one_to_one"
    )
    frame = frame.sort_values(["store_id", "product_id", "week_start"])
    frame["prior_8_week_avg_units"] = (
        frame.groupby(["store_id", "product_id"], observed=True)["units_sold"]
        .transform(lambda series: series.shift(1).rolling(8, min_periods=1).mean())
    )
    frame["expected_daily_units"] = (
        pd.concat(
            [frame["prior_8_week_avg_units"].div(7), frame["forecast_units"].div(7)],
            axis=1,
        )
        .max(axis=1)
        .fillna(0)
    )
    frame["estimated_lost_units"] = (
        frame["expected_daily_units"] * (7 - frame["in_stock_days"])
    ).clip(lower=0)
    frame = frame.merge(
        products[["product_id", "regular_unit_price"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    frame["estimated_lost_sales"] = (
        frame["estimated_lost_units"] * frame["regular_unit_price"]
    )
    return frame


def latest_weeks_of_cover(lost_sales_frame: pd.DataFrame) -> pd.DataFrame:
    latest_week = lost_sales_frame["week_start"].max()
    latest = lost_sales_frame[lost_sales_frame["week_start"] == latest_week].copy()
    demand = latest["prior_8_week_avg_units"].replace(0, pd.NA)
    latest["weeks_of_cover"] = latest["closing_stock_units"].div(demand)
    return latest

