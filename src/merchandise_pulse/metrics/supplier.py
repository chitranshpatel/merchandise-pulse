from __future__ import annotations

import pandas as pd


def purchase_order_lines(events: pd.DataFrame, as_of_date=None) -> pd.DataFrame:
    events = events[events["line_status"] != "Cancelled"].copy()
    if as_of_date is None:
        as_of_date = events[["expected_delivery_date", "actual_delivery_date"]].max().max()

    grouped = events.groupby("po_line_id", as_index=False).agg(
        purchase_order_id=("purchase_order_id", "first"),
        supplier_id=("supplier_id", "first"),
        product_id=("product_id", "first"),
        destination_store_id=("destination_store_id", "first"),
        expected_delivery_date=("expected_delivery_date", "first"),
        ordered_units=("ordered_units", "first"),
        received_units=("received_units", "sum"),
        final_receipt_date=("actual_delivery_date", "max"),
    )
    grouped["due_flag"] = grouped["expected_delivery_date"] <= as_of_date
    grouped = grouped[grouped["due_flag"]].copy()
    grouped["on_time_flag"] = (
        grouped["final_receipt_date"].notna()
        & (grouped["final_receipt_date"] <= grouped["expected_delivery_date"])
    )
    grouped["in_full_flag"] = grouped["received_units"] >= grouped["ordered_units"]
    grouped["otif_flag"] = grouped["on_time_flag"] & grouped["in_full_flag"]
    grouped["delivery_delay_days"] = (
        grouped["final_receipt_date"] - grouped["expected_delivery_date"]
    ).dt.days.clip(lower=0).fillna(0)
    return grouped


def supplier_service(lines: pd.DataFrame) -> pd.DataFrame:
    if lines.empty:
        return pd.DataFrame(columns=[
            "supplier_id", "due_lines", "on_time_pct", "in_full_pct", "otif_pct",
            "average_delivery_delay_days",
        ])
    return lines.groupby("supplier_id", as_index=False).agg(
        due_lines=("po_line_id", "nunique"),
        on_time_pct=("on_time_flag", "mean"),
        in_full_pct=("in_full_flag", "mean"),
        otif_pct=("otif_flag", "mean"),
        average_delivery_delay_days=("delivery_delay_days", "mean"),
    )

