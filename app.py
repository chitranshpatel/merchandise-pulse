from __future__ import annotations

from datetime import timedelta
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from merchandise_pulse.data import enrich_sales, load_quarantine_log, load_tables
from merchandise_pulse.exceptions import campaign_actions, combine_actions, planning_actions, supplier_actions
from merchandise_pulse.insights import build_evidence, brief_as_markdown, generate_openrouter_brief, template_brief
from merchandise_pulse.metrics.commercial import commercial_summary, sales_growth
from merchandise_pulse.metrics.forecast import forecast_detail, forecast_summary
from merchandise_pulse.metrics.inventory import add_lost_sales_estimate, inventory_summary, latest_weeks_of_cover
from merchandise_pulse.metrics.promotion import campaign_performance
from merchandise_pulse.metrics.supplier import purchase_order_lines, supplier_service
from merchandise_pulse.scoring import performance_band, supplier_score
from merchandise_pulse.validation import audit_tables


INK = "#14211A"
MOSS = "#55735B"
LIME = "#C9F27B"
CORAL = "#FF7657"
CREAM = "#F5F1E8"
MUTED = "#6E766F"


st.set_page_config(
    page_title="Merchandise Pulse",
    page_icon="◒",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');

    :root {{ --ink:{INK}; --moss:{MOSS}; --lime:{LIME}; --coral:{CORAL}; --cream:{CREAM}; }}
    .stApp {{ background: var(--cream); color: var(--ink); }}
    [data-testid="stHeader"] {{ background: transparent; }}
    [data-testid="stSidebar"] {{
        background: var(--ink);
        border-right: 0;
    }}
    [data-testid="stSidebar"] * {{ color: #F7F4EB; }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stDateInput label {{
        color: #B9C5BB !important; font-size: .72rem; text-transform: uppercase;
        letter-spacing: .09em; font-weight: 700;
    }}
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] {{
        background: #203229; border-color: #3D5146;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] {{ gap: .35rem; }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        background:#182B21; border:1px solid #30473A; border-radius:10px;
        padding:.55rem .7rem; transition:.15s ease;
    }}
    html, body, [class*="css"] {{ font-family: "DM Sans", sans-serif; }}
    h1, h2, h3 {{ font-family: "DM Serif Display", Georgia, serif !important; color: var(--ink); }}
    .block-container {{ max-width: 1440px; padding: 2.2rem 3rem 4rem; }}
    .brand-lockup {{ margin: 1rem 0 2.4rem; }}
    .brand-mark {{
        width: 34px; height: 34px; border-radius: 50%; background: var(--lime);
        color: var(--ink) !important; display: grid; place-items: center;
        font-size: 1.25rem; font-weight: 800; margin-bottom: .8rem;
    }}
    .brand-name {{ font-size: 1.12rem; font-weight: 700; letter-spacing: -.02em; }}
    .brand-sub {{ color: #92A197 !important; font-size: .78rem; margin-top: .2rem; }}
    .eyebrow {{
        font-size: .72rem; font-weight: 700; letter-spacing: .13em;
        text-transform: uppercase; color: var(--moss); margin-bottom: .65rem;
    }}
    .hero-title {{
        font-family: "DM Serif Display", Georgia, serif; font-size: clamp(2.7rem, 5vw, 5rem);
        line-height: .98; letter-spacing: -.045em; max-width: 900px; color: var(--ink);
    }}
    .hero-title em {{ color: var(--coral); font-style: normal; }}
    .hero-copy {{ max-width: 690px; color: var(--muted); font-size: 1.02rem; line-height: 1.6; margin: 1rem 0 2rem; }}
    .period-chip {{
        display: inline-flex; align-items: center; gap: .5rem; border: 1px solid #D8D5CC;
        border-radius: 999px; padding: .45rem .75rem; font-size: .78rem; font-weight: 600;
        background: #FFFDF8; margin-bottom: 1.1rem;
    }}
    .period-chip::before {{ content:""; width: 7px; height: 7px; background: var(--coral); border-radius: 50%; }}
    .kpi-card {{
        background: #FFFDF8; border: 1px solid #DEDAD0; border-radius: 18px;
        padding: 1.15rem 1.2rem 1rem; min-height: 132px;
        box-shadow: 0 8px 28px rgba(20,33,26,.04);
    }}
    .kpi-label {{ color: var(--muted); text-transform: uppercase; letter-spacing: .08em; font-size: .68rem; font-weight: 700; }}
    .kpi-value {{ font-family: "DM Serif Display", Georgia, serif; color: var(--ink); font-size: 2.05rem; line-height: 1.15; margin-top: .55rem; }}
    .kpi-foot {{ color: var(--muted); font-size: .76rem; margin-top: .55rem; }}
    .delta-up {{ color: #2D7A48; font-weight: 700; }}
    .delta-down {{ color: #C84C37; font-weight: 700; }}
    .section-kicker {{ margin-top: 2.5rem; color: var(--moss); text-transform: uppercase; font-size:.7rem; letter-spacing:.12em; font-weight:700; }}
    .section-title {{ font-family: "DM Serif Display", Georgia, serif; font-size: 2rem; letter-spacing: -.025em; margin: .2rem 0 1rem; }}
    .insight-card {{
        background: var(--ink); color: #F8F4EA; border-radius: 22px; padding: 1.5rem;
        min-height: 320px; position: relative; overflow: hidden;
    }}
    .insight-card::after {{ content:""; position:absolute; width:150px; height:150px; border-radius:50%; background:var(--lime); right:-70px; top:-60px; opacity:.9; }}
    .insight-number {{ color: var(--lime); font-size:.7rem; letter-spacing:.1em; text-transform:uppercase; font-weight:700; }}
    .insight-title {{ font-family:"DM Serif Display",Georgia,serif; font-size:1.65rem; line-height:1.08; margin:.65rem 0; max-width:85%; }}
    .insight-copy {{ color:#BDC9C0; line-height:1.55; font-size:.9rem; }}
    .insight-rule {{ height:1px; background:#385044; margin:1.25rem 0; }}
    .action-label {{ color:#93A399; font-size:.68rem; text-transform:uppercase; letter-spacing:.1em; font-weight:700; }}
    .action-copy {{ margin-top:.35rem; font-weight:600; font-size:.9rem; }}
    .chart-wrap {{ background:#FFFDF8; border:1px solid #DEDAD0; border-radius:22px; padding:.4rem .8rem .2rem; }}
    .supplier-rank {{
        display:flex; justify-content:space-between; align-items:center; gap:1rem;
        padding:.8rem 0; border-bottom:1px solid #E5E0D6;
    }}
    .rank-number {{ color:var(--coral); font-size:.72rem; font-weight:800; letter-spacing:.08em; }}
    .rank-name {{ color:var(--ink); font-weight:700; }}
    .rank-score {{ font-family:"DM Serif Display",Georgia,serif; font-size:1.4rem; color:var(--ink); }}
    .score-hero {{
        background:var(--lime); border-radius:22px; padding:1.4rem 1.5rem; min-height:172px;
        display:flex; flex-direction:column; justify-content:space-between;
    }}
    .score-number {{ font-family:"DM Serif Display",Georgia,serif; font-size:4rem; line-height:1; color:var(--ink); }}
    .score-band {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.11em; font-weight:800; color:var(--ink); }}
    .hierarchy-strip {{
        display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; margin:.75rem 0 1.2rem;
        color:var(--muted); font-size:.82rem;
    }}
    .hierarchy-node {{ background:#FFFDF8; border:1px solid #DCD7CD; border-radius:999px; padding:.42rem .7rem; }}
    .hierarchy-node strong {{ color:var(--ink); }}
    .hierarchy-arrow {{ color:var(--coral); font-weight:800; }}
    .stPlotlyChart {{ border-radius: 18px; overflow: hidden; }}
    div[data-testid="stMetric"] {{ background:transparent; }}
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ visibility: hidden; }}
    @media (max-width: 800px) {{ .block-container {{ padding:1.4rem 1rem 3rem; }} .hero-title {{ font-size:3rem; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False, ttl=60)
def get_data():
    return load_tables()


def compact_currency(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}m"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}k"
    return f"${value:,.0f}"


def pct(value: float | None, decimals: int = 1) -> str:
    if value is None:
        return "N/A"
    value = 0.0 if abs(value) < 0.0005 else value
    return f"{value:.{decimals}%}"


def kpi_card(label: str, value: str, foot: str, delta: float | None = None) -> None:
    delta_html = ""
    if delta is not None:
        css = "delta-up" if delta >= 0 else "delta-down"
        arrow = "↗" if delta >= 0 else "↘"
        delta_html = f'<span class="{css}">{arrow} {abs(delta):.1%}</span> · '
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-foot">{delta_html}{foot}</div></div>',
        unsafe_allow_html=True,
    )


tables = get_data()
all_sales = enrich_sales(tables)

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-mark">◒</div>'
        '<div class="brand-name">Merchandise Pulse</div>'
        '<div class="brand-sub">Health & beauty retail intelligence</div></div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "View",
        ["Executive Overview", "Supplier Scorecard", "Promotion Analysis", "Forecast & Inventory", "Action Centre", "AI Insight Brief", "Data Health"],
        label_visibility="collapsed",
    )
    st.caption(
        "A weekly view of trade, supply and forecast performance."
        if page == "Executive Overview"
        else "Compare supplier outcomes and open the drivers behind the score."
        if page == "Supplier Scorecard"
        else "Separate promotional volume from profitable incremental demand."
        if page == "Promotion Analysis"
        else "Review forecast accuracy, stock cover and availability exceptions."
        if page == "Forecast & Inventory"
        else "Prioritise cross-functional exceptions and track agreed actions."
        if page == "Action Centre"
        else "Generate a metric-grounded weekly brief with an optional OpenRouter model."
        if page == "AI Insight Brief"
        else "Review source controls, validation results and metric definitions."
    )
    min_week = all_sales["week_start"].min().date()
    max_week = all_sales["week_start"].max().date()
    default_start = max_week - timedelta(weeks=12)
    selected_dates = st.date_input(
        "Reporting period", value=(default_start, max_week), min_value=min_week, max_value=max_week
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date, end_date = default_start, max_week
    channels = st.multiselect("Channel", sorted(all_sales["channel"].unique()))
    categories = st.multiselect("Category", sorted(all_sales["category"].unique()))
    suppliers = st.multiselect("Supplier", sorted(all_sales["supplier_name"].unique()))
    st.markdown("---")
    st.caption("Synthetic demonstration data · refreshed from a fixed seed")


mask = all_sales["week_start"].dt.date.between(start_date, end_date)
filtered = all_sales.loc[mask].copy()
if channels:
    filtered = filtered[filtered["channel"].isin(channels)]
if categories:
    filtered = filtered[filtered["category"].isin(categories)]
if suppliers:
    filtered = filtered[filtered["supplier_name"].isin(suppliers)]

if filtered.empty:
    st.warning("No records match this filter combination. Try widening the reporting period.")
    st.stop()

selected_weeks = filtered["week_start"].nunique()
prior_end = pd.Timestamp(start_date - timedelta(weeks=1))
prior_start = prior_end - timedelta(weeks=max(selected_weeks - 1, 0))
prior = all_sales[all_sales["week_start"].between(prior_start, prior_end)].copy()
if channels:
    prior = prior[prior["channel"].isin(channels)]
if categories:
    prior = prior[prior["category"].isin(categories)]
if suppliers:
    prior = prior[prior["supplier_name"].isin(suppliers)]

current_commercial = commercial_summary(filtered)
prior_commercial = commercial_summary(prior)
growth = sales_growth(current_commercial["net_sales"], prior_commercial["net_sales"])

selected_keys = filtered[["week_start", "store_id", "product_id"]].drop_duplicates()
inventory = tables["fact_inventory_weekly"].merge(selected_keys, on=["week_start", "store_id", "product_id"])
forecasts = tables["fact_forecast_weekly"].merge(selected_keys, on=["week_start", "store_id", "product_id"])
sales_core = filtered[["week_start", "store_id", "product_id", "units_sold"]]
inventory_kpis = inventory_summary(inventory)
forecast_kpis = forecast_summary(forecast_detail(forecasts, sales_core))

lost = add_lost_sales_estimate(inventory, sales_core, forecasts, tables["dim_product"])
lost_sales = float(lost["estimated_lost_sales"].sum())

po_events = tables["fact_purchase_order_lines"]
po_events = po_events[po_events["expected_delivery_date"].dt.date.between(start_date, end_date)]
if suppliers:
    supplier_ids = set(filtered["supplier_id"])
    po_events = po_events[po_events["supplier_id"].isin(supplier_ids)]
service = supplier_service(purchase_order_lines(po_events, pd.Timestamp(end_date))) if not po_events.empty else pd.DataFrame()
otif = float((service["otif_pct"] * service["due_lines"]).sum() / service["due_lines"].sum()) if not service.empty else None


if page == "AI Insight Brief":
    weakest_supplier_name = None
    weakest_supplier_otif = None
    if not service.empty:
        weakest = service.sort_values("otif_pct").iloc[0]
        weakest_supplier_otif = float(weakest["otif_pct"])
        weakest_supplier_name = tables["dim_supplier"].set_index("supplier_id").loc[weakest["supplier_id"], "supplier_name"]

    period_label = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
    evidence = build_evidence(
        net_sales=current_commercial["net_sales"], sales_growth=growth,
        gross_margin_pct=current_commercial["gross_margin_pct"],
        availability_pct=inventory_kpis["availability_pct"],
        forecast_accuracy_pct=forecast_kpis["forecast_accuracy_pct"],
        forecast_bias_pct=forecast_kpis["forecast_bias_pct"], otif_pct=otif,
        lost_sales=lost_sales, weakest_supplier=weakest_supplier_name,
        weakest_supplier_otif=weakest_supplier_otif, period=period_label,
    )

    st.markdown('<div class="eyebrow">Merchandise initiatives · AI-assisted reporting</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">A weekly brief with<br><em>evidence attached.</em></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">The model receives a small set of aggregated metrics, not raw records. Every generated brief must cite the evidence supplied, and a rule-based version remains available without an API connection.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="period-chip">{period_label} · synthetic demonstration data</div>', unsafe_allow_html=True)

    try:
        secret_key = st.secrets.get("OPENROUTER_API_KEY", "")
    except FileNotFoundError:
        secret_key = ""
    configured_key = os.getenv("OPENROUTER_API_KEY", "") or secret_key

    setup_col, evidence_col = st.columns([1, 1.55], gap="large")
    with setup_col:
        st.markdown('<div class="section-kicker">Brief settings</div><div class="section-title">Generation controls</div>', unsafe_allow_html=True)
        audience = st.selectbox("Audience", ["Merchandise leadership", "Supplier manager", "Trade planning team"])
        model = st.text_input("OpenRouter model", value="openai/gpt-4o-mini", help="Enter any OpenRouter model slug that supports structured outputs.")
        entered_key = st.text_input(
            "OpenRouter API key", value="", type="password",
            placeholder="Using configured key" if configured_key else "sk-or-v1-…",
            help="Used for this request only. Do not commit API keys to Git.",
        )
        live_key = entered_key.strip() or configured_key
        generate = st.button("Generate live brief", type="primary", width="stretch", disabled=not bool(live_key))
        if not live_key:
            st.caption("Add a key here, set OPENROUTER_API_KEY, or create .streamlit/secrets.toml. Template mode is active.")
    with evidence_col:
        st.markdown('<div class="section-kicker">Model context</div><div class="section-title">Evidence supplied to the brief</div>', unsafe_allow_html=True)
        evidence_frame = pd.DataFrame(evidence)[["id", "metric", "display", "period"]].rename(
            columns={"id": "Evidence", "metric": "Metric", "display": "Value", "period": "Period"}
        )
        st.dataframe(evidence_frame, hide_index=True, width="stretch", height=332)

    brief = template_brief(evidence)
    mode = "Template fallback"
    if generate:
        with st.spinner("Preparing the evidence-grounded brief…"):
            try:
                brief = generate_openrouter_brief(
                    evidence, api_key=live_key, model=model.strip(), audience=audience
                )
                mode = f"OpenRouter · {model.strip()}"
                st.session_state["ai_brief"] = (brief, mode, evidence)
            except RuntimeError as exc:
                st.warning(f"Live generation was unavailable, so the template brief is shown. {exc}")
    elif "ai_brief" in st.session_state:
        saved_brief, saved_mode, saved_evidence = st.session_state["ai_brief"]
        if saved_evidence == evidence:
            brief, mode = saved_brief, saved_mode

    st.markdown('<div class="section-kicker">Generated output</div><div class="section-title">Weekly merchandise insight brief</div>', unsafe_allow_html=True)
    st.caption(f"Mode: {mode} · Confidence: {brief.confidence}")
    st.markdown(f"### {brief.headline}")
    b1, b2, b3 = st.columns(3, gap="medium")
    with b1:
        with st.container(border=True):
            st.caption("OBSERVED SITUATION")
            st.write(brief.situation)
    with b2:
        with st.container(border=True):
            st.caption("INTERPRETATION")
            st.write(brief.interpretation)
    with b3:
        with st.container(border=True):
            st.caption("RECOMMENDED ACTION")
            st.write(brief.recommendation)

    cited = pd.DataFrame([item for item in evidence if item["id"] in brief.evidence_ids])
    st.markdown('<div class="section-kicker">Traceability</div><div class="section-title">Evidence cited in the brief</div>', unsafe_allow_html=True)
    st.dataframe(
        cited[["id", "metric", "display", "period"]].rename(columns={"id": "Evidence", "metric": "Metric", "display": "Value", "period": "Period"}),
        hide_index=True, width="stretch",
    )
    markdown_export = brief_as_markdown(brief, evidence, mode=mode)
    st.download_button("Download brief", markdown_export, f"merchandise_brief_{end_date.isoformat()}.md", "text/markdown")
    st.caption("AI output is decision support, not an automated decision. A merchandise analyst should review interpretation and recommended actions.")
    st.stop()


if page == "Data Health":
    audits = audit_tables(tables)
    quarantine = load_quarantine_log()
    passed_checks = int((audits["status"] == "Pass").sum())
    failed_checks = int((audits["status"] == "Fail").sum())
    quality_score = 100 * passed_checks / len(audits)
    fact_rows = sum(len(tables[name]) for name in [
        "fact_sales_weekly", "fact_inventory_weekly", "fact_forecast_weekly", "fact_purchase_order_lines"
    ])
    latest_data_date = tables["fact_sales_weekly"]["week_start"].max()
    freshness_days = (pd.Timestamp("2026-08-10") - latest_data_date).days

    st.markdown('<div class="eyebrow">Reporting governance · Data health</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Trusted reporting starts<br><em>before the chart.</em></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Validation is applied at the business grain, failed source records are quarantined, and published metrics are calculated from the clean analytical model.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="period-chip">Latest trading week {latest_data_date.strftime("%d %b %Y")} · refreshed {freshness_days} days ago</div>',
        unsafe_allow_html=True,
    )

    d1, d2, d3, d4, d5 = st.columns(5, gap="small")
    with d1:
        kpi_card("Data-quality score", f"{quality_score:.0f}", "certified analytical layer")
    with d2:
        kpi_card("Checks passed", f"{passed_checks}/{len(audits)}", "live structural checks")
    with d3:
        kpi_card("Fact rows tested", f"{fact_rows / 1000:.0f}k", "sales, stock, forecast, orders")
    with d4:
        kpi_card("Rows quarantined", f"{len(quarantine)}", "excluded before reporting")
    with d5:
        kpi_card("Freshness", f"{freshness_days} days", "weekly reporting cadence")

    st.markdown('<div class="section-kicker">Data lineage</div><div class="section-title">Reporting flow and control points</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hierarchy-strip" style="margin-bottom:2rem">'
        '<span class="hierarchy-node"><strong>1 · Source staging</strong><br>Raw weekly extracts</span>'
        '<span class="hierarchy-arrow">→</span>'
        f'<span class="hierarchy-node"><strong>2 · Validation</strong><br>{len(quarantine)} rows quarantined</span>'
        '<span class="hierarchy-arrow">→</span>'
        f'<span class="hierarchy-node"><strong>3 · Curated model</strong><br>{fact_rows:,} fact rows</span>'
        '<span class="hierarchy-arrow">→</span>'
        '<span class="hierarchy-node"><strong>4 · Metric layer</strong><br>One formula per KPI</span>'
        '<span class="hierarchy-arrow">→</span>'
        '<span class="hierarchy-node"><strong>5 · Reporting</strong><br>Shared filters and actions</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-kicker">Validation results</div><div class="section-title">Control status by data domain</div>', unsafe_allow_html=True)
    validation_col, status_col = st.columns([1.8, 1], gap="medium")
    domain_status = audits.groupby("domain", as_index=False).agg(
        checks=("check", "count"), passed=("status", lambda values: (values == "Pass").sum()),
        failures=("failures", "sum"),
    )
    with validation_col:
        control_fig = go.Figure(go.Bar(
            x=domain_status["passed"], y=domain_status["domain"], orientation="h",
            marker_color=MOSS, customdata=domain_status[["checks", "failures"]],
            hovertemplate="<b>%{y}</b><br>Passed %{x} of %{customdata[0]}<br>Failures %{customdata[1]}<extra></extra>",
        ))
        control_fig.update_layout(
            height=340, margin=dict(l=10, r=20, t=20, b=15), paper_bgcolor="#FFFDF8", plot_bgcolor="#FFFDF8",
            font=dict(family="DM Sans", color=MUTED), xaxis=dict(title="Checks passed", dtick=1, gridcolor="#ECE8DE"),
            yaxis=dict(title=None),
        )
        st.plotly_chart(control_fig, width="stretch", config={"displayModeBar": False})
    with status_col:
        status_title = "All reporting controls passed" if failed_checks == 0 else f"{failed_checks} controls require attention"
        st.markdown(
            f'<div class="insight-card"><div class="insight-number">Certification status</div>'
            f'<div class="insight-title">{status_title}</div>'
            f'<div class="insight-copy">The published facts have unique business keys, valid mappings, reconciled sales values and valid date sequences.</div>'
            '<div class="insight-rule"></div><div class="action-label">Reporting decision</div>'
            '<div class="action-copy">The current analytical layer is suitable for the weekly merchandise review.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-kicker">Source exceptions</div><div class="section-title">Quarantined records excluded from reporting</div>', unsafe_allow_html=True)
    quarantine_display = quarantine.rename(columns={
        "issue_id": "Issue ID", "source_table": "Source", "record_key": "Record key",
        "rule": "Failed rule", "detected_date": "Detected", "status": "Status",
    })
    st.dataframe(
        quarantine_display, hide_index=True, width="stretch",
        column_config={"Detected": st.column_config.DateColumn(format="DD MMM YYYY")},
    )
    st.caption("These are deliberate synthetic source-quality examples. They are logged separately and never enter the clean facts used by the dashboard.")

    st.markdown('<div class="section-kicker">Metric governance</div><div class="section-title">Core KPI definitions used in reporting</div>', unsafe_allow_html=True)
    definitions = pd.DataFrame([
        ["Gross margin %", "(Net sales − cost of goods) ÷ net sales", "Product profitability before operating costs"],
        ["Availability %", "In-stock days ÷ possible ranged days", "Whether ranged products were available to customers"],
        ["Forecast bias", "Σ(forecast − actual) ÷ Σ actual", "Direction and scale of systematic forecast error"],
        ["Forecast accuracy", "max(0, 1 − WMAPE)", "Closeness of forecast units to actual units"],
        ["OTIF %", "Order lines on time and in full ÷ due lines", "Supplier delivery reliability"],
        ["Promotion ROTI", "Incremental GP after funding ÷ trade investment", "Return generated by promotional investment"],
        ["Estimated lost sales", "Expected daily units × out-of-stock days × regular price", "Opportunity estimate from constrained availability"],
    ], columns=["Metric", "Definition", "Business meaning"])
    st.dataframe(definitions, hide_index=True, width="stretch")
    st.caption("Detailed calculation conventions, edge cases and score thresholds are documented in docs/metric_dictionary.md.")
    st.stop()


if page == "Action Centre":
    product_lookup = tables["dim_product"][[
        "product_id", "product_name", "category", "supplier_id", "unit_cost"
    ]]
    supplier_lookup = tables["dim_supplier"][["supplier_id", "supplier_name", "otif_target"]]

    supplier_lost = lost.merge(
        product_lookup[["product_id", "supplier_id"]], on="product_id", how="left", validate="many_to_one"
    ).groupby("supplier_id", as_index=False).agg(lost_sales_exposure=("estimated_lost_sales", "sum"))
    supplier_queue = supplier_actions(service, supplier_lookup, supplier_lost) if not service.empty else pd.DataFrame()

    scoped_sales = all_sales.copy()
    if channels:
        scoped_sales = scoped_sales[scoped_sales["channel"].isin(channels)]
    if categories:
        scoped_sales = scoped_sales[scoped_sales["category"].isin(categories)]
    if suppliers:
        scoped_sales = scoped_sales[scoped_sales["supplier_name"].isin(suppliers)]
    active_promotions = tables["dim_promotion"][
        (tables["dim_promotion"]["start_date"].dt.date <= end_date)
        & (tables["dim_promotion"]["end_date"].dt.date >= start_date)
    ]
    action_campaigns = campaign_performance(
        scoped_sales, active_promotions, tables["bridge_promotion_products"]
    )
    promotion_queue = campaign_actions(action_campaigns) if not action_campaigns.empty else pd.DataFrame()

    action_forecasts = forecast_detail(forecasts, sales_core).merge(
        product_lookup, on="product_id", how="left", validate="many_to_one"
    ).merge(
        supplier_lookup[["supplier_id", "supplier_name"]],
        on="supplier_id", how="left", validate="many_to_one",
    )
    action_product_forecast = action_forecasts.groupby(
        ["product_id", "product_name", "category", "supplier_name", "unit_cost"], as_index=False
    ).agg(actual_units=("units_sold", "sum"), forecast_units=("forecast_units", "sum"), absolute_error=("absolute_error", "sum"))
    action_product_forecast["forecast_bias"] = (
        action_product_forecast["forecast_units"] - action_product_forecast["actual_units"]
    ) / action_product_forecast["actual_units"].replace(0, pd.NA)

    action_cover = latest_weeks_of_cover(lost).groupby("product_id", as_index=False).agg(
        closing_stock_units=("closing_stock_units", "sum"),
        average_weekly_demand=("prior_8_week_avg_units", "sum"),
        lost_sales_exposure=("estimated_lost_sales", "sum"),
        minimum_in_stock_days=("in_stock_days", "min"),
    )
    action_cover["weeks_of_cover"] = (
        action_cover["closing_stock_units"] / action_cover["average_weekly_demand"].replace(0, pd.NA)
    )
    action_planning = action_product_forecast.merge(action_cover, on="product_id", how="left")
    action_planning["exception"] = "Monitor"
    action_planning.loc[
        (action_planning["weeks_of_cover"] > 10) & (action_planning["forecast_bias"] > .10), "exception"
    ] = "Excess stock"
    action_planning.loc[
        (action_planning["lost_sales_exposure"] > 0) | (action_planning["minimum_in_stock_days"] < 7), "exception"
    ] = "Availability risk"
    inventory_queue = planning_actions(action_planning)
    actions = combine_actions(supplier_queue, promotion_queue, inventory_queue)

    st.markdown('<div class="eyebrow">Merchandise initiatives · Action workflow</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Convert exceptions into<br><em>owned actions.</em></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">A single queue connects the commercial signal, supporting evidence, financial exposure and the person responsible for the next decision.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="period-chip">{start_date.strftime("%d %b %Y")} — {end_date.strftime("%d %b %Y")} · {len(actions)} open actions</div>',
        unsafe_allow_html=True,
    )

    high_count = int((actions["priority"] == "High").sum())
    total_exposure = float(actions["impact_value"].sum())
    a1, a2, a3, a4 = st.columns(4, gap="small")
    with a1:
        kpi_card("High-priority actions", f"{high_count}", "requires current-cycle review")
    with a2:
        kpi_card("Financial exposure", compact_currency(total_exposure), "risk and opportunity estimate")
    with a3:
        kpi_card("Supplier actions", f"{int((actions['source'] == 'Supplier').sum())}", "service exceptions")
    with a4:
        kpi_card("Planning actions", f"{int((actions['source'] == 'Inventory').sum())}", "availability and excess stock")

    st.markdown('<div class="section-kicker">Workload profile</div><div class="section-title">Open actions by source and priority</div>', unsafe_allow_html=True)
    workload_col, focus_col = st.columns([1.75, 1], gap="medium")
    workload = actions.groupby(["source", "priority"], as_index=False).size()
    with workload_col:
        workload_fig = go.Figure()
        priority_colours = {"High": CORAL, "Medium": "#D49B43", "Low": MOSS}
        for priority in ["High", "Medium", "Low"]:
            group = workload[workload["priority"] == priority]
            if group.empty:
                continue
            workload_fig.add_trace(go.Bar(
                x=group["source"], y=group["size"], name=priority,
                marker_color=priority_colours[priority],
                hovertemplate="<b>%{x}</b><br>Actions %{y}<extra></extra>",
            ))
        workload_fig.update_layout(
            barmode="stack", height=350, margin=dict(l=10, r=10, t=30, b=15),
            paper_bgcolor="#FFFDF8", plot_bgcolor="#FFFDF8", font=dict(family="DM Sans", color=MUTED),
            legend=dict(orientation="h", y=1.12), xaxis=dict(title=None),
            yaxis=dict(title="Open actions", dtick=1, gridcolor="#ECE8DE"),
        )
        st.plotly_chart(workload_fig, width="stretch", config={"displayModeBar": False})
    with focus_col:
        top_action = actions.iloc[0]
        st.markdown(
            f'<div class="insight-card"><div class="insight-number">Priority action</div>'
            f'<div class="insight-title">{top_action["entity"]}</div>'
            f'<div class="insight-copy">{top_action["issue"]}. {top_action["evidence"]}. Estimated exposure {compact_currency(top_action["impact_value"])}.</div>'
            '<div class="insight-rule"></div><div class="action-label">Recommended action</div>'
            f'<div class="action-copy">{top_action["recommended_action"]}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-kicker">Action register</div><div class="section-title">Prioritised merchandise action queue</div>', unsafe_allow_html=True)
    q1, q2 = st.columns(2)
    with q1:
        priority_filter = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium"])
    with q2:
        source_filter = st.multiselect("Source", sorted(actions["source"].unique()), default=sorted(actions["source"].unique()))
    visible_actions = actions[
        actions["priority"].isin(priority_filter) & actions["source"].isin(source_filter)
    ].copy()
    editor_columns = [
        "priority", "source", "issue", "entity", "impact_value", "evidence",
        "recommended_action", "owner", "status",
    ]
    edited_actions = st.data_editor(
        visible_actions[editor_columns],
        hide_index=True,
        width="stretch",
        disabled=["priority", "source", "issue", "entity", "impact_value", "evidence", "recommended_action"],
        column_config={
            "priority": st.column_config.TextColumn("Priority"),
            "source": st.column_config.TextColumn("Source"),
            "issue": st.column_config.TextColumn("Issue"),
            "entity": st.column_config.TextColumn("Entity"),
            "impact_value": st.column_config.NumberColumn("Exposure", format="$%.0f"),
            "evidence": st.column_config.TextColumn("Evidence", width="large"),
            "recommended_action": st.column_config.TextColumn("Recommended action", width="large"),
            "owner": st.column_config.SelectboxColumn(
                "Owner", options=["Supplier Manager", "Trade Planner", "Merchandise Planner", "Merchandise Initiatives"]
            ),
            "status": st.column_config.SelectboxColumn(
                "Status", options=["Open", "In progress", "Blocked", "Complete"]
            ),
        },
        key="action_editor",
    )
    export = edited_actions.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download action register",
        data=export,
        file_name=f"merchandise_actions_{end_date.isoformat()}.csv",
        mime="text/csv",
    )
    st.caption("Action edits are session-based in this portfolio version. A production workflow would write owners, status changes and due dates back to a governed source.")
    st.stop()


if page == "Forecast & Inventory":
    forecast_rows = forecast_detail(forecasts, sales_core).merge(
        tables["dim_product"][["product_id", "product_name", "category", "supplier_id"]],
        on="product_id", how="left", validate="many_to_one",
    )
    forecast_rows = forecast_rows.merge(
        tables["dim_supplier"][["supplier_id", "supplier_name"]],
        on="supplier_id", how="left", validate="many_to_one",
    )
    overall_forecast = forecast_summary(forecast_rows)
    cover = latest_weeks_of_cover(lost)
    cover = cover.merge(
        tables["dim_product"][["product_id", "product_name", "category", "supplier_id"]],
        on="product_id", how="left", validate="many_to_one",
    )
    cover = cover.merge(
        tables["dim_supplier"][["supplier_id", "supplier_name"]],
        on="supplier_id", how="left", validate="many_to_one",
    )

    product_forecast = forecast_rows.groupby(
        ["product_id", "product_name", "category", "supplier_name"], as_index=False
    ).agg(actual_units=("units_sold", "sum"), forecast_units=("forecast_units", "sum"), absolute_error=("absolute_error", "sum"))
    product_forecast["forecast_bias"] = (
        product_forecast["forecast_units"] - product_forecast["actual_units"]
    ) / product_forecast["actual_units"].replace(0, pd.NA)
    product_forecast["forecast_accuracy"] = (
        1 - product_forecast["absolute_error"] / product_forecast["actual_units"].replace(0, pd.NA)
    ).clip(lower=0)

    product_cover = cover.groupby("product_id", as_index=False).agg(
        closing_stock_units=("closing_stock_units", "sum"),
        average_weekly_demand=("prior_8_week_avg_units", "sum"),
        lost_sales_exposure=("estimated_lost_sales", "sum"),
        minimum_in_stock_days=("in_stock_days", "min"),
    )
    product_cover["weeks_of_cover"] = (
        product_cover["closing_stock_units"] / product_cover["average_weekly_demand"].replace(0, pd.NA)
    )
    planning = product_forecast.merge(product_cover, on="product_id", how="left")
    planning["exception"] = "Monitor"
    planning.loc[(planning["weeks_of_cover"] > 10) & (planning["forecast_bias"] > 0.10), "exception"] = "Excess stock"
    planning.loc[(planning["lost_sales_exposure"] > 0) | (planning["minimum_in_stock_days"] < 7), "exception"] = "Availability risk"
    planning.loc[(planning["forecast_bias"].abs() <= 0.05) & (planning["weeks_of_cover"].between(2, 8)), "exception"] = "On plan"

    excess_units = int(planning.loc[planning["exception"] == "Excess stock", "closing_stock_units"].sum())
    exception_count = int((planning["exception"].isin(["Excess stock", "Availability risk"])).sum())

    st.markdown('<div class="eyebrow">Merchandise planning · Forecast and inventory</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Balance demand signals with<br><em>inventory exposure.</em></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">Forecast accuracy is most useful when it is connected to the stock outcome: lost availability, excess cover and the products requiring a planning decision.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="period-chip">{start_date.strftime("%d %b %Y")} — {end_date.strftime("%d %b %Y")} · latest stock snapshot {cover["week_start"].max().strftime("%d %b")}</div>',
        unsafe_allow_html=True,
    )

    f1, f2, f3, f4, f5 = st.columns(5, gap="small")
    with f1:
        kpi_card("Forecast accuracy", pct(overall_forecast["forecast_accuracy_pct"]), "WMAPE based")
    with f2:
        kpi_card("Forecast bias", pct(overall_forecast["forecast_bias_pct"]), "positive = over-forecast")
    with f3:
        kpi_card("Lost-sales exposure", compact_currency(lost_sales), "estimated opportunity")
    with f4:
        kpi_card("Excess-stock units", f"{excess_units:,}", "cover >10 weeks with bias")
    with f5:
        kpi_card("Priority SKUs", f"{exception_count}", "availability or excess risk")

    category_forecast = forecast_rows.groupby("category", as_index=False).agg(
        actual=("units_sold", "sum"), forecast=("forecast_units", "sum"), absolute_error=("absolute_error", "sum")
    )
    category_forecast["bias"] = (category_forecast["forecast"] - category_forecast["actual"]) / category_forecast["actual"]
    category_forecast["accuracy"] = (1 - category_forecast["absolute_error"] / category_forecast["actual"]).clip(lower=0)
    category_forecast = category_forecast.sort_values("bias")

    st.markdown('<div class="section-kicker">Forecast performance</div><div class="section-title">Forecast bias and accuracy by category</div>', unsafe_allow_html=True)
    bias_col, context_col = st.columns([2, 1], gap="medium")
    with bias_col:
        bias_fig = go.Figure(go.Bar(
            x=category_forecast["bias"], y=category_forecast["category"], orientation="h",
            marker=dict(color=[CORAL if abs(value) > .05 else MOSS for value in category_forecast["bias"]]),
            customdata=category_forecast[["accuracy", "actual"]],
            hovertemplate="<b>%{y}</b><br>Bias %{x:.1%}<br>Accuracy %{customdata[0]:.1%}<br>Actual units %{customdata[1]:,.0f}<extra></extra>",
        ))
        bias_fig.add_vrect(x0=-.05, x1=.05, fillcolor="rgba(201,242,123,.22)", line_width=0)
        bias_fig.add_vline(x=0, line_color=INK, line_width=1)
        bias_fig.update_layout(
            height=390, margin=dict(l=10, r=20, t=15, b=20), paper_bgcolor="#FFFDF8", plot_bgcolor="#FFFDF8",
            font=dict(family="DM Sans", color=MUTED), xaxis=dict(tickformat=".0%", title="Forecast bias", gridcolor="#ECE8DE"),
            yaxis=dict(title=None), showlegend=False,
        )
        st.plotly_chart(bias_fig, width="stretch", config={"displayModeBar": False})
    with context_col:
        worst_category = category_forecast.iloc[(category_forecast["bias"].abs()).argmax()]
        direction = "over-forecast" if worst_category["bias"] > 0 else "under-forecast"
        st.markdown(
            f'<div class="insight-card"><div class="insight-number">Planning signal</div>'
            f'<div class="insight-title">{worst_category["category"]} has the largest systematic bias</div>'
            f'<div class="insight-copy">The category is {direction} by {abs(worst_category["bias"]):.1%}, outside the ±5% working tolerance.</div>'
            '<div class="insight-rule"></div><div class="action-label">Suggested next move</div>'
            '<div class="action-copy">Review seasonality and promotional assumptions, then reconcile the next forecast against current cover.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-kicker">Inventory position</div><div class="section-title">SKU forecast bias and weeks of cover</div>', unsafe_allow_html=True)
    risk_colours = {"Excess stock": CORAL, "Availability risk": "#D49B43", "Monitor": "#9AA79D", "On plan": MOSS}
    stock_fig = go.Figure()
    for label, group in planning.groupby("exception"):
        stock_fig.add_trace(go.Scatter(
            x=group["forecast_bias"], y=group["weeks_of_cover"], mode="markers", name=label,
            text=group["product_name"],
            customdata=group[["supplier_name", "forecast_accuracy", "closing_stock_units", "lost_sales_exposure"]],
            marker=dict(color=risk_colours[label], size=(group["actual_units"] / max(planning["actual_units"].max(), 1) * 18 + 8), opacity=.78),
            hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>Bias %{x:.1%}<br>Cover %{y:.1f} weeks<br>Accuracy %{customdata[1]:.1%}<br>Closing units %{customdata[2]:,.0f}<br>Lost-sales exposure $%{customdata[3]:,.0f}<extra></extra>",
        ))
    stock_fig.add_vrect(x0=-.05, x1=.05, fillcolor="rgba(201,242,123,.14)", line_width=0)
    stock_fig.add_hline(y=10, line_dash="dash", line_color=CORAL, annotation_text="10-week excess threshold")
    stock_fig.update_layout(
        height=460, margin=dict(l=15, r=15, t=40, b=20), paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        font=dict(family="DM Sans", color=MUTED), legend=dict(orientation="h", y=1.12),
        xaxis=dict(tickformat=".0%", title="Forecast bias", gridcolor="#DEDAD0"),
        yaxis=dict(title="Weeks of cover", gridcolor="#DEDAD0", rangemode="tozero"),
    )
    st.plotly_chart(stock_fig, width="stretch", config={"displayModeBar": False})

    st.markdown('<div class="section-kicker">Exception queue</div><div class="section-title">Products requiring planning action</div>', unsafe_allow_html=True)
    exceptions = planning[planning["exception"].isin(["Excess stock", "Availability risk"])].copy()
    exceptions["recommended_action"] = exceptions["exception"].map({
        "Excess stock": "Reduce or defer replenishment; review forecast",
        "Availability risk": "Check inbound supply and store allocation",
    })
    exceptions = exceptions.sort_values(["lost_sales_exposure", "weeks_of_cover"], ascending=[False, False]).head(15)
    display_exceptions = exceptions[[
        "exception", "product_name", "supplier_name", "category", "forecast_bias",
        "weeks_of_cover", "lost_sales_exposure", "recommended_action",
    ]].rename(columns={
        "exception": "Issue", "product_name": "Product", "supplier_name": "Supplier",
        "category": "Category", "forecast_bias": "Bias", "weeks_of_cover": "Weeks cover",
        "lost_sales_exposure": "Lost-sales exposure", "recommended_action": "Recommended action",
    })
    display_exceptions["Bias"] = display_exceptions["Bias"] * 100
    st.dataframe(
        display_exceptions,
        hide_index=True,
        width="stretch",
        column_config={
            "Bias": st.column_config.NumberColumn(format="%.1f%%"),
            "Weeks cover": st.column_config.NumberColumn(format="%.1f"),
            "Lost-sales exposure": st.column_config.NumberColumn(format="$%.0f"),
        },
    )
    st.caption("Forecast bias is aggregated over the selected period. Weeks of cover uses the latest selected stock snapshot and the prior eight-week demand run rate.")
    st.stop()


if page == "Promotion Analysis":
    scoped_sales = all_sales.copy()
    if channels:
        scoped_sales = scoped_sales[scoped_sales["channel"].isin(channels)]
    if categories:
        scoped_sales = scoped_sales[scoped_sales["category"].isin(categories)]
    if suppliers:
        scoped_sales = scoped_sales[scoped_sales["supplier_name"].isin(suppliers)]

    promo_dim = tables["dim_promotion"]
    active_promotions = promo_dim[
        (promo_dim["start_date"].dt.date <= end_date)
        & (promo_dim["end_date"].dt.date >= start_date)
    ]
    campaigns = campaign_performance(
        scoped_sales,
        active_promotions,
        tables["bridge_promotion_products"],
    )
    if campaigns.empty:
        st.warning("No completed campaigns with a usable baseline match this selection.")
        st.stop()

    lost_with_promo = lost.merge(
        filtered[["week_start", "store_id", "product_id", "promotion_id"]],
        on=["week_start", "store_id", "product_id"],
        how="left",
        validate="one_to_one",
    )
    promo_exposure = lost_with_promo.groupby("promotion_id", as_index=False).agg(
        stockout_exposure=("estimated_lost_sales", "sum")
    )
    campaigns = campaigns.merge(promo_exposure, on="promotion_id", how="left")
    campaigns["stockout_exposure"] = campaigns["stockout_exposure"].fillna(0)
    campaigns["decision"] = campaigns.apply(
        lambda row: "Stop & redesign"
        if row["incremental_gp_after_funding"] <= 0
        else "Funding-dependent"
        if row["incremental_gp_before_funding"] < 0
        else "Scale with control",
        axis=1,
    )

    total_incremental_gp = float(campaigns["incremental_gp_after_funding"].sum())
    total_funding = float(campaigns["supplier_funding"].sum())
    median_uplift = float(campaigns["promotional_uplift_pct"].median())
    profitable_share = float((campaigns["incremental_gp_after_funding"] > 0).mean())

    st.markdown('<div class="eyebrow">Trade investment · Campaign review</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Volume gets attention.<br><em>Incremental profit earns it.</em></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">A promotion is only successful when the demand is genuinely incremental, the margin holds, and supplier funding does not hide weak product economics.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="period-chip">{start_date.strftime("%d %b %Y")} — {end_date.strftime("%d %b %Y")} · {len(campaigns)} campaigns</div>',
        unsafe_allow_html=True,
    )

    p1, p2, p3, p4 = st.columns(4, gap="small")
    with p1:
        kpi_card("Incremental GP", compact_currency(total_incremental_gp), "after supplier funding")
    with p2:
        kpi_card("Median uplift", pct(median_uplift), "vs eight-week baseline")
    with p3:
        kpi_card("Profitable campaigns", pct(profitable_share, 0), "positive incremental GP")
    with p4:
        kpi_card("Supplier funding", compact_currency(total_funding), "allocated to included SKUs")

    st.markdown('<div class="section-kicker">Campaign portfolio</div><div class="section-title">Campaign uplift and incremental gross profit</div>', unsafe_allow_html=True)
    scatter_col, decision_col = st.columns([2.1, 1], gap="medium")
    with scatter_col:
        colour_map = {"Scale with control": MOSS, "Funding-dependent": "#D49B43", "Stop & redesign": CORAL}
        scatter = go.Figure()
        for decision, group in campaigns.groupby("decision"):
            scatter.add_trace(go.Scatter(
                x=group["promotional_uplift_pct"],
                y=group["incremental_gp_after_funding"],
                mode="markers",
                name=decision,
                text=group["promotion_name"],
                customdata=group[["promotion_sales", "roti", "stockout_exposure"]],
                marker=dict(
                    color=colour_map[decision],
                    size=(group["promotion_sales"] / max(campaigns["promotion_sales"].max(), 1) * 26 + 12),
                    opacity=.82,
                    line=dict(color="#FFFDF8", width=2),
                ),
                hovertemplate="<b>%{text}</b><br>Uplift %{x:.1%}<br>Incremental GP $%{y:,.0f}<br>Sales $%{customdata[0]:,.0f}<br>ROTI %{customdata[1]:.2f}<br>Stock-out exposure $%{customdata[2]:,.0f}<extra></extra>",
            ))
        scatter.add_hline(y=0, line_dash="dash", line_color="#9A9F9A")
        scatter.update_layout(
            height=430, margin=dict(l=15, r=15, t=35, b=20), paper_bgcolor="#FFFDF8", plot_bgcolor="#FFFDF8",
            font=dict(family="DM Sans", color=MUTED), legend=dict(orientation="h", y=1.12),
            xaxis=dict(tickformat=".0%", title="Promotional uplift", gridcolor="#ECE8DE"),
            yaxis=dict(tickprefix="$", tickformat="~s", title="Incremental GP after funding", gridcolor="#ECE8DE"),
        )
        st.plotly_chart(scatter, width="stretch", config={"displayModeBar": False})
    with decision_col:
        decision_counts = campaigns["decision"].value_counts()
        risk_campaign = campaigns.sort_values("incremental_gp_after_funding").iloc[0]
        st.markdown(
            f'<div class="insight-card"><div class="insight-number">Trade decision</div>'
            f'<div class="insight-title">{risk_campaign["promotion_name"]} needs the first review</div>'
            f'<div class="insight-copy">Its incremental GP after funding is {compact_currency(risk_campaign["incremental_gp_after_funding"])} '
            f'with {pct(risk_campaign["promotional_uplift_pct"])} uplift. {int(decision_counts.get("Stop & redesign", 0))} campaign(s) currently destroy value after funding.</div>'
            '<div class="insight-rule"></div><div class="action-label">Suggested next move</div>'
            '<div class="action-copy">Review discount depth, supplier funding and stock availability before repeating the mechanic.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-kicker">Campaign drill-down</div><div class="section-title">Campaign financial bridge and decision</div>', unsafe_allow_html=True)
    campaign_name = st.selectbox(
        "Open campaign",
        campaigns.sort_values("incremental_gp_after_funding")["promotion_name"].tolist(),
    )
    campaign = campaigns[campaigns["promotion_name"] == campaign_name].iloc[0]
    detail_a, detail_b = st.columns([1.45, 1], gap="medium")
    with detail_a:
        waterfall = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Baseline GP", "Promotion effect", "Supplier funding", "Promo GP after funding"],
            y=[
                campaign["baseline_gross_profit"],
                campaign["incremental_gp_before_funding"],
                campaign["supplier_funding"],
                campaign["incremental_gp_after_funding"],
            ],
            connector={"line": {"color": "#BFC3BE"}},
            increasing={"marker": {"color": MOSS}}, decreasing={"marker": {"color": CORAL}},
            totals={"marker": {"color": INK}},
            hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>",
        ))
        waterfall.update_layout(
            height=380, margin=dict(l=10, r=10, t=20, b=15), paper_bgcolor="#FFFDF8", plot_bgcolor="#FFFDF8",
            font=dict(family="DM Sans", color=MUTED), yaxis=dict(tickprefix="$", tickformat="~s", gridcolor="#ECE8DE"),
            showlegend=False,
        )
        st.plotly_chart(waterfall, width="stretch", config={"displayModeBar": False})
    with detail_b:
        st.markdown(
            f'<div class="kpi-card" style="min-height:380px"><div class="kpi-label">{campaign["promotion_type"]} · {campaign["channel"]}</div>'
            f'<div class="kpi-value">{campaign["decision"]}</div>'
            f'<div class="supplier-rank"><span class="rank-name">Promotion sales</span><span class="rank-score">{compact_currency(campaign["promotion_sales"])}</span></div>'
            f'<div class="supplier-rank"><span class="rank-name">Incremental GP</span><span class="rank-score">{compact_currency(campaign["incremental_gp_after_funding"])}</span></div>'
            f'<div class="supplier-rank"><span class="rank-name">Incremental units</span><span class="rank-score">{campaign["incremental_units"]:,.0f}</span></div>'
            f'<div class="supplier-rank"><span class="rank-name">ROTI</span><span class="rank-score">{campaign["roti"]:.2f}</span></div>'
            f'<div class="supplier-rank"><span class="rank-name">Stock-out exposure</span><span class="rank-score">{compact_currency(campaign["stockout_exposure"])}</span></div></div>',
            unsafe_allow_html=True,
        )
    st.caption("Baseline uses the median of up to eight eligible non-promotional weeks. Incremental GP before funding remains visible so supplier funding cannot conceal weak customer economics.")
    st.stop()


if page == "Supplier Scorecard":
    supplier_dim = tables["dim_supplier"][["supplier_id", "supplier_name", "supplier_tier", "otif_target"]]
    product_supplier = tables["dim_product"][["product_id", "supplier_id"]]

    supplier_sales = filtered.groupby(["supplier_id", "supplier_name"], as_index=False).agg(
        net_sales=("net_sales", "sum"),
        cost=("cost_of_goods", "sum"),
        units=("units_sold", "sum"),
    )
    supplier_sales["gross_margin"] = (supplier_sales["net_sales"] - supplier_sales["cost"]) / supplier_sales["net_sales"]

    prior_supplier = prior.groupby("supplier_id", as_index=False).agg(prior_sales=("net_sales", "sum"))
    supplier_sales = supplier_sales.merge(prior_supplier, on="supplier_id", how="left")
    supplier_sales["sales_growth"] = (
        supplier_sales["net_sales"] - supplier_sales["prior_sales"]
    ) / supplier_sales["prior_sales"].replace(0, pd.NA)

    supplier_inventory = inventory.merge(product_supplier, on="product_id", how="left", validate="many_to_one")
    supplier_availability = supplier_inventory.groupby("supplier_id", as_index=False).agg(
        in_stock_days=("in_stock_days", "sum"), ranged_rows=("ranged_flag", "sum")
    )
    supplier_availability["availability"] = supplier_availability["in_stock_days"] / (supplier_availability["ranged_rows"] * 7)

    supplier_forecasts = forecast_detail(forecasts, sales_core).merge(
        product_supplier, on="product_id", how="left", validate="many_to_one"
    )
    supplier_forecast = supplier_forecasts.groupby("supplier_id", as_index=False).agg(
        actual=("units_sold", "sum"), absolute_error=("absolute_error", "sum")
    )
    supplier_forecast["forecast_accuracy"] = (
        1 - supplier_forecast["absolute_error"] / supplier_forecast["actual"].replace(0, pd.NA)
    ).clip(lower=0)

    scorecard = (
        supplier_sales.merge(supplier_availability[["supplier_id", "availability"]], on="supplier_id", how="left")
        .merge(supplier_forecast[["supplier_id", "forecast_accuracy"]], on="supplier_id", how="left")
        .merge(service[["supplier_id", "due_lines", "otif_pct"]] if not service.empty else pd.DataFrame(columns=["supplier_id", "due_lines", "otif_pct"]), on="supplier_id", how="left")
        .merge(supplier_dim, on=["supplier_id", "supplier_name"], how="left")
    )
    scorecard["score"] = scorecard.apply(
        lambda row: supplier_score({
            "otif": row["otif_pct"] if pd.notna(row["otif_pct"]) else None,
            "availability": row["availability"] if pd.notna(row["availability"]) else None,
            "sales_growth": row["sales_growth"] if pd.notna(row["sales_growth"]) else None,
            "gross_margin": row["gross_margin"] if pd.notna(row["gross_margin"]) else None,
            "forecast_accuracy": row["forecast_accuracy"] if pd.notna(row["forecast_accuracy"]) else None,
            "promotion_roti": None,
            "data_quality": 1.0,
        }),
        axis=1,
    )
    scorecard["band"] = scorecard["score"].map(performance_band)
    scorecard = scorecard.sort_values("score", ascending=False).reset_index(drop=True)

    st.markdown('<div class="eyebrow">Strategic supplier · Performance review</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Better conversations start with<br><em>one shared score.</em></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-copy">A balanced view of service, availability, trade and forecast performance—with the underlying drivers kept close enough to challenge.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="period-chip">{start_date.strftime("%d %b %Y")} — {end_date.strftime("%d %b %Y")} · {len(scorecard)} suppliers</div>',
        unsafe_allow_html=True,
    )

    available_names = scorecard["supplier_name"].tolist()
    selected_supplier_name = st.selectbox(
        "Open supplier",
        available_names,
        index=len(available_names) - 1,
        help="The lowest-ranked supplier is opened by default.",
    )
    selected = scorecard[scorecard["supplier_name"] == selected_supplier_name].iloc[0]
    selected_catalogue = tables["dim_product"][tables["dim_product"]["supplier_id"] == selected["supplier_id"]]
    brand_count = selected_catalogue["brand"].nunique()
    product_count = selected_catalogue["product_id"].nunique()
    st.markdown(
        f'<div class="hierarchy-strip"><span class="hierarchy-node"><strong>{selected_supplier_name}</strong> · supplier company</span>'
        f'<span class="hierarchy-arrow">→</span><span class="hierarchy-node"><strong>{brand_count}</strong> consumer brands</span>'
        f'<span class="hierarchy-arrow">→</span><span class="hierarchy-node"><strong>{product_count}</strong> products / SKUs</span></div>',
        unsafe_allow_html=True,
    )

    score_col, metric_col = st.columns([1, 3], gap="medium")
    with score_col:
        st.markdown(
            f'<div class="score-hero"><div><div class="kpi-label">Composite score</div>'
            f'<div class="score-number">{selected["score"]:.0f}</div></div>'
            f'<div class="score-band">{selected["band"]} · {selected["supplier_tier"]}</div></div>',
            unsafe_allow_html=True,
        )
    with metric_col:
        m1, m2, m3, m4 = st.columns(4, gap="small")
        with m1:
            kpi_card("OTIF", pct(selected["otif_pct"] if pd.notna(selected["otif_pct"]) else None), f'target {selected["otif_target"]:.0%}')
        with m2:
            kpi_card("Availability", pct(selected["availability"]), "ranged store–SKU days")
        with m3:
            kpi_card("Sales growth", pct(selected["sales_growth"]), "vs prior matched period")
        with m4:
            kpi_card("Forecast accuracy", pct(selected["forecast_accuracy"]), "WMAPE based")

    st.markdown('<div class="section-kicker">Score components</div><div class="section-title">Supplier KPI performance against target</div>', unsafe_allow_html=True)
    anatomy_col, ranking_col = st.columns([1.75, 1], gap="medium")
    component_labels = ["OTIF", "Availability", "Sales growth", "Gross margin", "Forecast accuracy", "Data quality"]
    component_values = [
        selected["otif_pct"] if pd.notna(selected["otif_pct"]) else 0,
        selected["availability"], selected["sales_growth"], selected["gross_margin"],
        selected["forecast_accuracy"], 1.0,
    ]
    component_targets = [float(selected["otif_target"]), 0.97, 0.05, 0.40, 0.85, 1.0]
    with anatomy_col:
        component_fig = go.Figure()
        component_fig.add_trace(go.Bar(
            y=component_labels, x=component_values, orientation="h", name="Actual",
            marker=dict(color=[CORAL if actual < target else MOSS for actual, target in zip(component_values, component_targets)]),
            customdata=component_targets,
            hovertemplate="<b>%{y}</b><br>Actual %{x:.1%}<br>Target %{customdata:.1%}<extra></extra>",
        ))
        component_fig.add_trace(go.Scatter(
            y=component_labels, x=component_targets, mode="markers", name="Target",
            marker=dict(color=INK, size=10, symbol="line-ns-open", line=dict(width=2)),
            hovertemplate="Target %{x:.1%}<extra></extra>",
        ))
        component_fig.update_layout(
            height=390, barmode="overlay", margin=dict(l=8, r=20, t=30, b=15),
            paper_bgcolor="#FFFDF8", plot_bgcolor="#FFFDF8", font=dict(family="DM Sans", color=MUTED),
            legend=dict(orientation="h", y=1.12), xaxis=dict(tickformat=".0%", gridcolor="#ECE8DE", range=[min(-0.12, min(component_values) * 1.2), 1.05]),
            yaxis=dict(autorange="reversed", title=None),
        )
        st.plotly_chart(component_fig, width="stretch", config={"displayModeBar": False})
    with ranking_col:
        rank_rows = "".join(
            f'<div class="supplier-rank"><div><span class="rank-number">{index + 1:02d}</span> '
            f'<span class="rank-name">{row["supplier_name"]}</span></div><div class="rank-score">{row["score"]:.0f}</div></div>'
            for index, row in scorecard.head(6).iterrows()
        )
        st.markdown(
            f'<div class="kpi-card" style="min-height:390px"><div class="kpi-label">Supplier ranking</div>{rank_rows}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-kicker">Brand and product drivers</div><div class="section-title">Top SKU sales and margin contribution</div>', unsafe_allow_html=True)
    supplier_products = filtered[filtered["supplier_id"] == selected["supplier_id"]].groupby(
        ["product_id", "product_name"], as_index=False
    ).agg(net_sales=("net_sales", "sum"), units=("units_sold", "sum"), cost=("cost_of_goods", "sum"))
    supplier_products["gross_margin_pct"] = (supplier_products["net_sales"] - supplier_products["cost"]) / supplier_products["net_sales"]
    supplier_products = supplier_products.sort_values("net_sales", ascending=False).head(8)
    product_fig = go.Figure(go.Bar(
        x=supplier_products["product_name"], y=supplier_products["net_sales"],
        marker=dict(color=supplier_products["gross_margin_pct"], colorscale=[[0, "#AAB6AD"], [1, LIME]]),
        customdata=supplier_products[["gross_margin_pct", "units"]],
        hovertemplate="<b>%{x}</b><br>Sales $%{y:,.0f}<br>Margin %{customdata[0]:.1%}<br>Units %{customdata[1]:,.0f}<extra></extra>",
    ))
    product_fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=10, b=100), paper_bgcolor=CREAM, plot_bgcolor=CREAM,
        font=dict(family="DM Sans", color=MUTED), xaxis=dict(tickangle=-28, title=None),
        yaxis=dict(gridcolor="#DEDAD0", tickprefix="$", tickformat="~s", title=None),
    )
    st.plotly_chart(product_fig, width="stretch", config={"displayModeBar": False})
    st.caption("Supplier means the company fulfilling the commercial relationship. Brands are the customer-facing names within its range. The composite score uses transparent weights; promotion return is temporarily omitted and the remaining weights are rebalanced.")
    st.stop()

st.markdown('<div class="eyebrow">Weekly trading room · Executive view</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-title">See the signal.<br><em>Act on the exception.</em></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-copy">One view across sales, margin, availability, supplier delivery and forecast health—built to move a weekly review from reporting to action.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="period-chip">{start_date.strftime("%d %b %Y")} — {end_date.strftime("%d %b %Y")} · {selected_weeks} weeks</div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns([1.1, 1, 1, 1, 1], gap="small")
with k1:
    kpi_card("Net sales", compact_currency(current_commercial["net_sales"]), "vs prior matched period", growth)
with k2:
    margin_delta = None
    if prior_commercial["gross_margin_pct"] is not None:
        margin_delta = current_commercial["gross_margin_pct"] - prior_commercial["gross_margin_pct"]
    kpi_card("Gross margin", pct(current_commercial["gross_margin_pct"]), "change in margin", margin_delta)
with k3:
    kpi_card("Availability", pct(inventory_kpis["availability_pct"]), "target 97%")
with k4:
    kpi_card("Forecast accuracy", pct(forecast_kpis["forecast_accuracy_pct"]), "WMAPE based")
with k5:
    kpi_card("Supplier OTIF", pct(otif), f"{int(service['due_lines'].sum()) if not service.empty else 0:,} due lines")

st.markdown('<div class="section-kicker">Performance trend</div><div class="section-title">Weekly sales and gross margin</div>', unsafe_allow_html=True)
chart_col, insight_col = st.columns([2.25, 1], gap="medium")

weekly = filtered.groupby("week_start", as_index=False).agg(net_sales=("net_sales", "sum"), cost=("cost_of_goods", "sum"))
weekly["gross_margin_pct"] = (weekly["net_sales"] - weekly["cost"]) / weekly["net_sales"]
with chart_col:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["week_start"], y=weekly["net_sales"], mode="lines",
        line=dict(color=INK, width=3, shape="spline"),
        fill="tozeroy", fillcolor="rgba(85,115,91,.12)", name="Net sales",
        hovertemplate="%{x|%d %b}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=weekly["week_start"], y=weekly["gross_margin_pct"], mode="lines+markers",
        line=dict(color=CORAL, width=2), marker=dict(size=5), yaxis="y2", name="Gross margin",
        hovertemplate="%{x|%d %b}<br>%{y:.1%}<extra></extra>",
    ))
    fig.update_layout(
        height=390, margin=dict(l=16, r=16, t=44, b=12), paper_bgcolor="#FFFDF8",
        plot_bgcolor="#FFFDF8", font=dict(family="DM Sans", color=MUTED),
        legend=dict(orientation="h", y=1.14, x=0, title=None), hovermode="x unified",
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#ECE8DE", tickprefix="$", tickformat="~s", title=None),
        yaxis2=dict(overlaying="y", side="right", tickformat=".0%", showgrid=False, title=None),
    )
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with insight_col:
    weakest_supplier = service.sort_values("otif_pct").iloc[0] if not service.empty else None
    weakest_name = "No supplier selected"
    weakest_otif = None
    if weakest_supplier is not None:
        supplier_row = tables["dim_supplier"].set_index("supplier_id").loc[weakest_supplier["supplier_id"]]
        weakest_name = supplier_row["supplier_name"]
        weakest_otif = float(weakest_supplier["otif_pct"])
    insight_title = f"{weakest_name} is the first supplier to review" if weakest_otif is not None else "Review current supply coverage"
    fact = f"OTIF is {weakest_otif:.1%}, below the 95% working target." if weakest_otif is not None else "There are no due purchase-order lines in this selection."
    st.markdown(
        f'<div class="insight-card"><div class="insight-number">Priority signal 01</div>'
        f'<div class="insight-title">{insight_title}</div><div class="insight-copy">{fact} '
        f'The selected view also carries {compact_currency(lost_sales)} in estimated lost-sales exposure.</div>'
        '<div class="insight-rule"></div><div class="action-label">Suggested next move</div>'
        '<div class="action-copy">Open late order lines, check stock exposure, then agree recovery dates before the next campaign.</div></div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-kicker">Category performance</div><div class="section-title">Category sales and gross margin</div>', unsafe_allow_html=True)
category = filtered.groupby("category", as_index=False).agg(net_sales=("net_sales", "sum"), cost=("cost_of_goods", "sum"), units=("units_sold", "sum"))
category["gross_margin_pct"] = (category["net_sales"] - category["cost"]) / category["net_sales"]
category = category.sort_values("net_sales")
bar = go.Figure(go.Bar(
    x=category["net_sales"], y=category["category"], orientation="h",
    marker=dict(color=category["gross_margin_pct"], colorscale=[[0, "#9FB1A3"], [1, LIME]], line=dict(width=0)),
    customdata=category[["gross_margin_pct", "units"]],
    hovertemplate="<b>%{y}</b><br>Sales $%{x:,.0f}<br>Margin %{customdata[0]:.1%}<br>Units %{customdata[1]:,.0f}<extra></extra>",
))
bar.update_layout(
    height=360, margin=dict(l=8, r=18, t=10, b=20), paper_bgcolor=CREAM, plot_bgcolor=CREAM,
    font=dict(family="DM Sans", color=MUTED), xaxis=dict(showgrid=True, gridcolor="#DEDAD0", tickprefix="$", tickformat="~s", title=None),
    yaxis=dict(showgrid=False, title=None),
)
st.plotly_chart(bar, width="stretch", config={"displayModeBar": False})

st.caption("All figures use synthetic data. Estimated lost sales are an opportunity measure, not recognised revenue.")
