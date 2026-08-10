from __future__ import annotations

import pandas as pd

from .commercial import safe_divide


def forecast_detail(forecasts: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    keys = ["week_start", "store_id", "product_id"]
    detail = forecasts.merge(
        sales[keys + ["units_sold"]], on=keys, how="inner", validate="one_to_one"
    )
    detail["forecast_error"] = detail["forecast_units"] - detail["units_sold"]
    detail["absolute_error"] = detail["forecast_error"].abs()
    return detail


def forecast_summary(detail: pd.DataFrame) -> dict[str, float | None]:
    actual = float(detail["units_sold"].sum())
    bias = safe_divide(float(detail["forecast_error"].sum()), actual)
    wmape = safe_divide(float(detail["absolute_error"].sum()), actual)
    return {
        "forecast_bias_pct": bias,
        "wmape": wmape,
        "forecast_accuracy_pct": None if wmape is None else max(0.0, 1 - wmape),
    }

