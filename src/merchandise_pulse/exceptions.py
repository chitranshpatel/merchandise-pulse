from __future__ import annotations

import pandas as pd


ACTION_COLUMNS = [
    "action_id", "source", "priority", "issue", "entity", "impact_value",
    "evidence", "recommended_action", "owner", "status",
]


def supplier_actions(
    service: pd.DataFrame,
    suppliers: pd.DataFrame,
    lost_sales_by_supplier: pd.DataFrame,
) -> pd.DataFrame:
    frame = service.merge(
        suppliers[["supplier_id", "supplier_name", "otif_target"]],
        on="supplier_id", how="left", validate="one_to_one",
    ).merge(lost_sales_by_supplier, on="supplier_id", how="left")
    frame["lost_sales_exposure"] = frame["lost_sales_exposure"].fillna(0)
    frame = frame[frame["otif_pct"] < frame["otif_target"]].copy()
    rows = []
    for row in frame.itertuples(index=False):
        gap = row.otif_target - row.otif_pct
        priority = "High" if gap >= .15 or row.lost_sales_exposure >= 5_000 else "Medium"
        rows.append({
            "action_id": f"SUP-{row.supplier_id}", "source": "Supplier",
            "priority": priority, "issue": "OTIF below target", "entity": row.supplier_name,
            "impact_value": row.lost_sales_exposure,
            "evidence": f"OTIF {row.otif_pct:.1%} vs {row.otif_target:.1%} target; {int(row.due_lines)} due lines",
            "recommended_action": "Review late order lines and agree supplier recovery dates",
            "owner": "Supplier Manager", "status": "Open",
        })
    return pd.DataFrame(rows, columns=ACTION_COLUMNS)


def campaign_actions(campaigns: pd.DataFrame) -> pd.DataFrame:
    flagged = campaigns[
        (campaigns["incremental_gp_after_funding"] <= 0)
        | (campaigns["incremental_gp_before_funding"] < 0)
    ]
    rows = []
    for row in flagged.itertuples(index=False):
        destroys_value = row.incremental_gp_after_funding <= 0
        rows.append({
            "action_id": f"PRM-{row.promotion_id}", "source": "Promotion",
            "priority": "High" if destroys_value else "Medium",
            "issue": "Negative incremental profit" if destroys_value else "Funding-dependent result",
            "entity": row.promotion_name,
            "impact_value": abs(min(0, row.incremental_gp_after_funding)),
            "evidence": f"Uplift {row.promotional_uplift_pct:.1%}; incremental GP ${row.incremental_gp_after_funding:,.0f}; ROTI {row.roti:.2f}",
            "recommended_action": "Review discount depth and funding before repeating campaign",
            "owner": "Trade Planner", "status": "Open",
        })
    return pd.DataFrame(rows, columns=ACTION_COLUMNS)


def planning_actions(planning: pd.DataFrame) -> pd.DataFrame:
    flagged = planning[planning["exception"].isin(["Excess stock", "Availability risk"])]
    rows = []
    for row in flagged.itertuples(index=False):
        availability = row.exception == "Availability risk"
        impact = row.lost_sales_exposure if availability else row.closing_stock_units * row.unit_cost
        high = row.lost_sales_exposure >= 250 or row.weeks_of_cover >= 14
        rows.append({
            "action_id": f"PLN-{row.product_id}", "source": "Inventory",
            "priority": "High" if high else "Medium",
            "issue": row.exception, "entity": row.product_name,
            "impact_value": float(impact),
            "evidence": (
                f"Lost-sales exposure ${row.lost_sales_exposure:,.0f}; cover {row.weeks_of_cover:.1f} weeks"
                if availability else
                f"Cover {row.weeks_of_cover:.1f} weeks; forecast bias {row.forecast_bias:.1%}"
            ),
            "recommended_action": (
                "Check inbound supply and store allocation"
                if availability else "Reduce or defer replenishment and review forecast"
            ),
            "owner": "Merchandise Planner", "status": "Open",
        })
    return pd.DataFrame(rows, columns=ACTION_COLUMNS)


def combine_actions(*frames: pd.DataFrame) -> pd.DataFrame:
    usable = [frame for frame in frames if not frame.empty]
    if not usable:
        return pd.DataFrame(columns=ACTION_COLUMNS)
    result = pd.concat(usable, ignore_index=True)
    order = pd.Categorical(result["priority"], categories=["High", "Medium", "Low"], ordered=True)
    return result.assign(_priority_order=order).sort_values(
        ["_priority_order", "impact_value"], ascending=[True, False]
    ).drop(columns="_priority_order").reset_index(drop=True)
