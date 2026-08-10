from __future__ import annotations

import pandas as pd


def safe_divide(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def commercial_summary(sales: pd.DataFrame) -> dict[str, float | None]:
    net_sales = float(sales["net_sales"].sum())
    cost = float(sales["cost_of_goods"].sum())
    gross_profit = net_sales - cost
    return {
        "net_sales": net_sales,
        "units_sold": int(sales["units_sold"].sum()),
        "gross_profit": gross_profit,
        "gross_margin_pct": safe_divide(gross_profit, net_sales),
    }


def sales_growth(current_sales: float, comparison_sales: float) -> float | None:
    return safe_divide(current_sales - comparison_sales, comparison_sales)

