from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .commercial import safe_divide


def promotion_summary(
    promotion_sales: pd.DataFrame,
    baseline_units: float,
    regular_unit_price: float,
    unit_cost: float,
    supplier_funding: float,
) -> dict[str, float | None]:
    promo_units = float(promotion_sales["units_sold"].sum())
    promo_sales = float(promotion_sales["net_sales"].sum())
    promo_cost = float(promotion_sales["cost_of_goods"].sum())
    discount = float(promotion_sales["discount_value"].sum())
    incremental_units = promo_units - baseline_units
    baseline_gp = baseline_units * (regular_unit_price - unit_cost)
    promo_gp = promo_sales - promo_cost
    incremental_before = promo_gp - baseline_gp
    incremental_after = incremental_before + supplier_funding
    investment = discount + supplier_funding
    return {
        "promotion_units": promo_units,
        "baseline_units": baseline_units,
        "incremental_units": incremental_units,
        "promotional_uplift_pct": safe_divide(incremental_units, baseline_units),
        "incremental_gp_before_funding": incremental_before,
        "incremental_gp_after_funding": incremental_after,
        "roti": safe_divide(incremental_after, investment),
    }


def baseline_from_history(history: pd.DataFrame, campaign_weeks: int) -> float | None:
    weekly = history.groupby("week_start", as_index=False)["units_sold"].sum()
    if len(weekly) < 4:
        return None
    return float(weekly.tail(8)["units_sold"].median() * campaign_weeks)


def campaign_performance(
    sales: pd.DataFrame,
    promotions: pd.DataFrame,
    bridge: pd.DataFrame,
) -> pd.DataFrame:
    """Return one row per campaign using an eight-week non-promo baseline."""
    rows = []
    for promotion in promotions.itertuples(index=False):
        promotion_start = pd.Timestamp(promotion.start_date)
        promotion_end = pd.Timestamp(promotion.end_date)
        products = bridge[bridge["promotion_id"] == promotion.promotion_id]
        if products.empty:
            continue
        campaign_sales = sales[sales["promotion_id"] == promotion.promotion_id]
        if campaign_sales.empty:
            continue

        campaign_weeks = max(1, ((promotion_end - promotion_start).days + 7) // 7)
        baseline_units = 0.0
        baseline_gp = 0.0
        eligible_products = 0
        for product in products.itertuples(index=False):
            product_sales = campaign_sales[campaign_sales["product_id"] == product.product_id]
            if product_sales.empty:
                continue
            history = sales[
                (sales["product_id"] == product.product_id)
                & (sales["channel"] == promotion.channel)
                & (sales["week_start"] < promotion_start)
                & (sales["week_start"] >= promotion_start - timedelta(weeks=8))
                & (sales["promotion_id"].isna())
            ]
            product_baseline = baseline_from_history(history, campaign_weeks)
            if product_baseline is None:
                continue
            cost = float(product_sales["unit_cost"].iloc[0])
            price = float(product_sales["regular_unit_price"].iloc[0])
            baseline_units += product_baseline
            baseline_gp += product_baseline * (price - cost)
            eligible_products += 1

        if eligible_products == 0:
            continue
        promo_units = float(campaign_sales["units_sold"].sum())
        promo_sales = float(campaign_sales["net_sales"].sum())
        promo_cost = float(campaign_sales["cost_of_goods"].sum())
        discount = float(campaign_sales["discount_value"].sum())
        funding = float(products.loc[products["product_id"].isin(campaign_sales["product_id"]), "funding_allocation"].sum())
        promo_gp = promo_sales - promo_cost
        incremental_before = promo_gp - baseline_gp
        incremental_after = incremental_before + funding
        investment = discount + funding
        rows.append({
            "promotion_id": promotion.promotion_id,
            "promotion_name": promotion.promotion_name,
            "promotion_type": promotion.promotion_type,
            "channel": promotion.channel,
            "start_date": promotion.start_date,
            "end_date": promotion.end_date,
            "eligible_products": eligible_products,
            "promotion_units": promo_units,
            "promotion_sales": promo_sales,
            "promotion_gross_profit": promo_gp,
            "baseline_units": baseline_units,
            "baseline_gross_profit": baseline_gp,
            "incremental_units": promo_units - baseline_units,
            "promotional_uplift_pct": safe_divide(promo_units - baseline_units, baseline_units),
            "supplier_funding": funding,
            "discount_value": discount,
            "incremental_gp_before_funding": incremental_before,
            "incremental_gp_after_funding": incremental_after,
            "roti": safe_divide(incremental_after, investment),
        })
    return pd.DataFrame(rows)
