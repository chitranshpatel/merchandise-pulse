from datetime import timedelta

import pandas as pd
import pytest

from merchandise_pulse.data import TABLES, load_tables
from merchandise_pulse.metrics.commercial import commercial_summary, sales_growth
from merchandise_pulse.metrics.forecast import forecast_detail, forecast_summary
from merchandise_pulse.metrics.inventory import inventory_summary
from merchandise_pulse.metrics.promotion import baseline_from_history, campaign_performance, promotion_summary
from merchandise_pulse.metrics.supplier import purchase_order_lines, supplier_service
from merchandise_pulse.scoring import component_score, performance_band, supplier_score
from merchandise_pulse.validation import audit_tables, data_quality_score
from merchandise_pulse.exceptions import campaign_actions, combine_actions, supplier_actions
from merchandise_pulse.insights import build_evidence, brief_as_markdown, template_brief


def test_commercial_summary_uses_ratio_of_totals():
    sales = pd.DataFrame({
        "net_sales": [100.0, 300.0],
        "cost_of_goods": [60.0, 150.0],
        "units_sold": [5, 10],
    })
    result = commercial_summary(sales)
    assert result["gross_profit"] == 190.0
    assert result["gross_margin_pct"] == pytest.approx(0.475)
    assert sales_growth(110, 100) == pytest.approx(0.10)
    assert sales_growth(10, 0) is None


def test_inventory_summary_excludes_unranged_rows():
    inventory = pd.DataFrame({
        "ranged_flag": [True, True, False],
        "in_stock_days": [7, 5, 0],
        "closing_stock_units": [10, 4, 99],
    })
    result = inventory_summary(inventory)
    assert result["availability_pct"] == pytest.approx(12 / 14)
    assert result["closing_stock_units"] == 14


def test_forecast_bias_and_wmape_have_distinct_meanings():
    forecasts = pd.DataFrame({
        "week_start": pd.to_datetime(["2026-01-05", "2026-01-12"]),
        "store_id": ["A", "A"], "product_id": ["X", "X"],
        "forecast_units": [120, 80],
    })
    sales = pd.DataFrame({
        "week_start": pd.to_datetime(["2026-01-05", "2026-01-12"]),
        "store_id": ["A", "A"], "product_id": ["X", "X"],
        "units_sold": [100, 100],
    })
    result = forecast_summary(forecast_detail(forecasts, sales))
    assert result["forecast_bias_pct"] == 0
    assert result["wmape"] == pytest.approx(0.20)
    assert result["forecast_accuracy_pct"] == pytest.approx(0.80)


def test_split_deliveries_are_counted_once_for_otif():
    events = pd.DataFrame({
        "po_line_id": ["L1", "L1", "L2"],
        "purchase_order_id": ["P1", "P1", "P2"],
        "supplier_id": ["S1", "S1", "S1"],
        "product_id": ["A", "A", "B"],
        "destination_store_id": ["X", "X", "X"],
        "expected_delivery_date": pd.to_datetime(["2026-01-10"] * 3),
        "actual_delivery_date": pd.to_datetime(["2026-01-09", "2026-01-10", "2026-01-12"]),
        "ordered_units": [100, 100, 50],
        "received_units": [60, 40, 50],
        "line_status": ["Complete", "Complete", "Complete"],
    })
    lines = purchase_order_lines(events, pd.Timestamp("2026-01-20"))
    result = supplier_service(lines).iloc[0]
    assert result["due_lines"] == 2
    assert result["in_full_pct"] == 1
    assert result["otif_pct"] == pytest.approx(0.5)


def test_promotion_profit_includes_funding_only_after_base_result():
    sales = pd.DataFrame({
        "units_sold": [15], "net_sales": [120.0],
        "cost_of_goods": [75.0], "discount_value": [30.0],
    })
    result = promotion_summary(sales, 10, 10, 5, 20)
    assert result["incremental_gp_before_funding"] == -5
    assert result["incremental_gp_after_funding"] == 15
    assert result["roti"] == pytest.approx(0.3)


def test_baseline_needs_four_weeks():
    short = pd.DataFrame({"week_start": [1, 2, 3], "units_sold": [5, 6, 7]})
    assert baseline_from_history(short, 1) is None


def test_campaign_performance_separates_funding_from_product_economics():
    weeks = pd.date_range("2026-01-05", periods=10, freq="W-MON")
    sales = pd.DataFrame({
        "week_start": weeks,
        "product_id": ["A"] * 10,
        "channel": ["Beauty Retail"] * 10,
        "promotion_id": [None] * 8 + ["P1", "P1"],
        "units_sold": [10] * 8 + [16, 16],
        "net_sales": [100.0] * 8 + [128.0, 128.0],
        "cost_of_goods": [50.0] * 8 + [80.0, 80.0],
        "discount_value": [0.0] * 8 + [32.0, 32.0],
        "unit_cost": [5.0] * 10,
        "regular_unit_price": [10.0] * 10,
    })
    promotions = pd.DataFrame({
        "promotion_id": ["P1"], "promotion_name": ["Launch"],
        "promotion_type": ["Percentage"], "channel": ["Beauty Retail"],
        "start_date": [weeks[8]], "end_date": [weeks[9] + timedelta(days=6)],
    })
    bridge = pd.DataFrame({
        "promotion_id": ["P1"], "product_id": ["A"], "funding_allocation": [30.0]
    })
    result = campaign_performance(sales, promotions, bridge).iloc[0]
    assert result["baseline_units"] == 20
    assert result["incremental_units"] == 12
    assert result["incremental_gp_before_funding"] == -4
    assert result["incremental_gp_after_funding"] == 26


def test_supplier_score_clamps_and_reweights_missing_components():
    assert component_score(2, 0, 1) == 100
    values = {
        "otif": 0.95,
        "availability": 0.97,
        "sales_growth": None,
        "gross_margin": None,
        "forecast_accuracy": None,
        "promotion_roti": None,
        "data_quality": None,
    }
    assert supplier_score(values) == pytest.approx(100)
    assert performance_band(54.9) == "Action required"


def test_data_quality_penalties_are_capped():
    assert data_quality_score(duplicates=100) == 75
    assert data_quality_score(duplicates=100, missing_mappings=100,
                              invalid_negative_values=100,
                              invalid_date_sequences=100,
                              stale_required_table=True) == 0


def test_action_queue_prioritises_material_supplier_and_campaign_issues():
    service = pd.DataFrame({
        "supplier_id": ["S1"], "due_lines": [20], "otif_pct": [.70]
    })
    suppliers = pd.DataFrame({
        "supplier_id": ["S1"], "supplier_name": ["Supplier One"], "otif_target": [.95]
    })
    exposure = pd.DataFrame({"supplier_id": ["S1"], "lost_sales_exposure": [6000.0]})
    supplier = supplier_actions(service, suppliers, exposure)
    campaign = campaign_actions(pd.DataFrame({
        "promotion_id": ["P1"], "promotion_name": ["Campaign One"],
        "incremental_gp_after_funding": [-1000.0],
        "incremental_gp_before_funding": [-1200.0],
        "promotional_uplift_pct": [.40], "roti": [-.2],
    }))
    result = combine_actions(campaign, supplier)
    assert result.iloc[0]["priority"] == "High"
    assert set(result["source"]) == {"Supplier", "Promotion"}
    assert result["action_id"].is_unique


def test_audit_tables_reports_clean_core_tables():
    sales = pd.DataFrame({
        "week_start": [pd.Timestamp("2026-01-05")], "store_id": ["A"],
        "product_id": ["P"], "gross_sales": [10.0], "discount_value": [2.0],
        "net_sales": [8.0],
    })
    tables = {
        "fact_sales_weekly": sales,
        "fact_inventory_weekly": pd.DataFrame({
            "week_start": [pd.Timestamp("2026-01-05")], "store_id": ["A"],
            "product_id": ["P"], "in_stock_days": [7], "closing_stock_units": [2],
        }),
        "fact_forecast_weekly": pd.DataFrame({
            "week_start": [pd.Timestamp("2026-01-05")], "store_id": ["A"],
            "product_id": ["P"], "forecast_version": ["V1"],
        }),
        "fact_purchase_order_lines": pd.DataFrame({
            "delivery_event_id": ["D1"], "order_date": [pd.Timestamp("2026-01-01")],
            "actual_delivery_date": [pd.Timestamp("2026-01-04")],
        }),
        "dim_product": pd.DataFrame({"product_id": ["P"]}),
        "dim_store": pd.DataFrame({"store_id": ["A"]}),
        "dim_promotion": pd.DataFrame({
            "start_date": [pd.Timestamp("2026-01-01")], "end_date": [pd.Timestamp("2026-01-07")]
        }),
    }
    result = audit_tables(tables)
    assert len(result) == 11
    assert (result["status"] == "Pass").all()


def test_template_insight_is_traceable_to_supplied_evidence():
    evidence = build_evidence(
        net_sales=100_000, sales_growth=.03, gross_margin_pct=.45,
        availability_pct=.96, forecast_accuracy_pct=.76, forecast_bias_pct=.08,
        otif_pct=.88, lost_sales=4_500, weakest_supplier="Supplier One",
        weakest_supplier_otif=.72, period="01 Jan 2026 to 31 Jan 2026",
    )
    brief = template_brief(evidence)
    allowed_ids = {item["id"] for item in evidence}
    assert set(brief.evidence_ids).issubset(allowed_ids)
    assert "Supplier" in brief.headline
    exported = brief_as_markdown(brief, evidence, mode="Template fallback")
    assert "Supplier One OTIF" in exported
    assert "synthetic portfolio data" in exported


def test_missing_deployment_data_is_generated_automatically(tmp_path):
    tables = load_tables(tmp_path / "generated")
    assert set(tables) == set(TABLES)
    assert all(not frame.empty for frame in tables.values())
