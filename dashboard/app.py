"""Streamlit dashboard for Ontario housing market and data quality metrics."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.data_service import load_dashboard_data as load_local_data

CITY_COLORS = {
    "Toronto": "#64d8ff",
    "Mississauga": "#a78bfa",
    "Brampton": "#f59e0b",
    "Ottawa": "#34d399",
    "Hamilton": "#fb7185",
    "Oshawa": "#60a5fa",
}


@st.cache_data
def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    return load_local_data()


def currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value / 1_000:.0f}K"


def percent_delta(current: float, previous: float) -> str:
    if previous == 0 or pd.isna(previous):
        return "No prior period"
    return f"{(current / previous - 1) * 100:+.1f}% vs prior month"


def style_chart(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=48, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#dce7f3", family="Inter, sans-serif"),
        title_font=dict(size=17, color="#f5f8fc"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="#111c2d", font_color="#f8fafc"),
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.10)", linecolor="#29364a")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.10)", linecolor="#29364a")
    return fig


st.set_page_config(
    page_title="Ontario Housing Observatory",
    page_icon="OH",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --ink: #f5f8fc;
        --muted: #91a4bb;
        --panel: rgba(17, 28, 45, 0.82);
        --line: rgba(148, 163, 184, 0.16);
        --cyan: #64d8ff;
    }

    .stApp {
        background:
            radial-gradient(circle at 82% 2%, rgba(29, 107, 145, 0.23), transparent 30%),
            radial-gradient(circle at 15% 28%, rgba(77, 63, 140, 0.15), transparent 26%),
            #07111f;
        color: var(--ink);
        font-family: "DM Sans", sans-serif;
    }

    h1, h2, h3, [data-testid="stMetricValue"] {
        font-family: "Space Grotesk", sans-serif !important;
        letter-spacing: -0.03em;
    }

    [data-testid="stSidebar"] {
        background: rgba(8, 18, 32, 0.96);
        border-right: 1px solid var(--line);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 1500px;
    }

    .hero {
        border: 1px solid var(--line);
        background: linear-gradient(125deg, rgba(18, 41, 63, 0.94), rgba(10, 22, 38, 0.82));
        padding: 30px 34px;
        border-radius: 22px;
        margin-bottom: 22px;
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.22);
    }

    .eyebrow {
        color: var(--cyan);
        text-transform: uppercase;
        letter-spacing: 0.14em;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .hero h1 {
        margin: 0;
        font-size: clamp(2rem, 4vw, 3.5rem);
        line-height: 1.03;
    }

    .hero p {
        color: #a9bacd;
        max-width: 760px;
        margin: 12px 0 0;
        font-size: 1.02rem;
    }

    [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 18px 20px;
        min-height: 128px;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
    }

    [data-testid="stMetricValue"] {
        color: var(--ink);
    }

    [data-testid="stPlotlyChart"], [data-testid="stDataFrame"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 8px;
        overflow: hidden;
    }

    .section-title {
        font-family: "Space Grotesk", sans-serif;
        font-size: 1.35rem;
        font-weight: 600;
        margin: 24px 0 12px;
    }

    .quality-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 22px;
        min-height: 188px;
    }

    .quality-score {
        font-family: "Space Grotesk", sans-serif;
        font-size: 3rem;
        font-weight: 700;
        color: #34d399;
        line-height: 1;
    }

    .quality-label {
        color: var(--muted);
        margin-top: 8px;
    }

    .status-pill {
        display: inline-block;
        background: rgba(52, 211, 153, 0.12);
        color: #6ee7b7;
        border: 1px solid rgba(52, 211, 153, 0.28);
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-top: 14px;
    }

    .small-note {
        color: var(--muted);
        font-size: 0.84rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

silver, gold, quality, anomalies = load_dashboard_data()

with st.sidebar:
    st.markdown("## Ontario Observatory")
    st.caption("Market intelligence and data health")
    st.divider()

    all_cities = sorted(gold["city"].unique())
    selected_cities = st.multiselect(
        "Cities",
        all_cities,
        default=all_cities,
        help="Select one or more cities to compare.",
    )
    min_month = gold["month"].min().date()
    max_month = gold["month"].max().date()
    selected_range = st.date_input(
        "Reporting period",
        value=(min_month, max_month),
        min_value=min_month,
        max_value=max_month,
    )
    st.divider()
    st.caption("Synthetic demonstration data")
    st.caption(f"Updated through {max_month:%B %Y}")

if not selected_cities:
    st.warning("Select at least one city in the sidebar.")
    st.stop()

if isinstance(selected_range, tuple) and len(selected_range) == 2:
    start_date, end_date = selected_range
else:
    start_date, end_date = min_month, max_month

filtered_gold = gold[
    gold["city"].isin(selected_cities)
    & gold["month"].dt.date.between(start_date, end_date)
].copy()
filtered_silver = silver[
    silver["city"].isin(selected_cities)
    & silver["sale_date"].dt.date.between(start_date, end_date)
].copy()
filtered_anomalies = anomalies[
    anomalies["city"].isin(selected_cities)
    & anomalies["month"].dt.date.between(start_date, end_date)
].copy()

st.markdown(
    """
    <div class="hero">
        <div class="eyebrow">Ontario market pulse</div>
        <h1>Housing intelligence,<br/>with the data health attached.</h1>
        <p>Track market direction across six Ontario cities while monitoring
        the quality signals that make every metric trustworthy.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

latest_month = filtered_gold["month"].max()
current = filtered_gold[filtered_gold["month"] == latest_month]
previous_month = latest_month - pd.offsets.MonthBegin(1)
previous = filtered_gold[filtered_gold["month"] == previous_month]

current_price = current["average_price"].mean()
previous_price = previous["average_price"].mean()
current_sales = int(current["sales_volume"].sum())
previous_sales = int(previous["sales_volume"].sum())
current_dom = current["average_days_on_market"].mean()
previous_dom = previous["average_days_on_market"].mean()

metric_columns = st.columns(4)
metric_columns[0].metric(
    "Average sale price",
    currency(current_price),
    percent_delta(current_price, previous_price),
)
metric_columns[1].metric(
    "Monthly sales",
    f"{current_sales:,}",
    percent_delta(current_sales, previous_sales),
)
metric_columns[2].metric(
    "Days on market",
    f"{current_dom:.1f}",
    f"{current_dom - previous_dom:+.1f} days vs prior month",
    delta_color="inverse",
)
metric_columns[3].metric(
    "Quality score",
    f"{quality['quality_score']:.0f}%",
    "All controls passing" if all(quality["checks"].values()) else "Review required",
)

st.markdown('<div class="section-title">Market movement</div>', unsafe_allow_html=True)
left_chart, right_chart = st.columns([1.65, 1])

with left_chart:
    price_fig = px.line(
        filtered_gold,
        x="month",
        y="average_price",
        color="city",
        color_discrete_map=CITY_COLORS,
        markers=True,
        title="Average sale price by city",
        labels={"month": "", "average_price": "Average price", "city": ""},
    )
    price_fig.update_yaxes(tickprefix="$", tickformat=",.0f")
    price_fig.update_traces(line=dict(width=2.5), marker=dict(size=5))
    st.plotly_chart(style_chart(price_fig), width="stretch")

with right_chart:
    latest_by_city = (
        filtered_gold.sort_values("month").groupby("city", as_index=False).tail(1)
    )
    rank_fig = px.bar(
        latest_by_city.sort_values("average_price"),
        x="average_price",
        y="city",
        orientation="h",
        color="city",
        color_discrete_map=CITY_COLORS,
        title=f"Price position - {latest_month:%b %Y}",
        labels={"average_price": "", "city": ""},
    )
    rank_fig.update_xaxes(tickprefix="$", tickformat=",.0s")
    rank_fig.update_layout(showlegend=False)
    st.plotly_chart(style_chart(rank_fig), width="stretch")

volume_fig = px.bar(
    filtered_gold,
    x="month",
    y="sales_volume",
    color="city",
    color_discrete_map=CITY_COLORS,
    title="Monthly sales volume",
    labels={"month": "", "sales_volume": "Transactions", "city": ""},
    barmode="group",
)
st.plotly_chart(style_chart(volume_fig, height=390), width="stretch")

st.markdown('<div class="section-title">Trust and exceptions</div>', unsafe_allow_html=True)
quality_col, anomaly_col = st.columns([0.75, 2])

with quality_col:
    passed_checks = sum(quality["checks"].values())
    total_checks = len(quality["checks"])
    st.markdown(
        f"""
        <div class="quality-card">
            <div class="eyebrow">Data quality</div>
            <div class="quality-score">{quality["quality_score"]:.0f}%</div>
            <div class="quality-label">{passed_checks} of {total_checks} controls passing</div>
            <div class="status-pill">Pipeline healthy</div>
            <p class="small-note">{quality["row_count"]:,} silver records evaluated</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with anomaly_col:
    if filtered_anomalies.empty:
        st.success("No month-over-month changes exceeded the 20% threshold.")
    else:
        anomaly_plot = filtered_anomalies.copy()
        anomaly_plot["direction"] = anomaly_plot["mom_change_percent"].apply(
            lambda value: "Increase" if value > 0 else "Decrease"
        )
        anomaly_fig = px.scatter(
            anomaly_plot,
            x="month",
            y="mom_change_percent",
            size=anomaly_plot["mom_change_percent"].abs(),
            color="direction",
            hover_name="city",
            hover_data={"metric": True, "current_value": ":,.0f"},
            color_discrete_map={"Increase": "#34d399", "Decrease": "#fb7185"},
            title="Detected month-over-month anomalies",
            labels={"month": "", "mom_change_percent": "Change (%)", "direction": ""},
        )
        anomaly_fig.add_hline(y=20, line_dash="dot", line_color="#64748b")
        anomaly_fig.add_hline(y=-20, line_dash="dot", line_color="#64748b")
        st.plotly_chart(style_chart(anomaly_fig, height=330), width="stretch")

st.markdown('<div class="section-title">Recent market activity</div>', unsafe_allow_html=True)
table_data = filtered_silver.sort_values("sale_date", ascending=False).head(100).copy()
table_data["sale_price"] = table_data["sale_price"].map(lambda value: f"${value:,.0f}")
table_data["sale_date"] = table_data["sale_date"].dt.strftime("%b %d, %Y")
table_data = table_data.rename(
    columns={
        "record_id": "Record",
        "city": "City",
        "sale_date": "Sale date",
        "property_type": "Property type",
        "sale_price": "Sale price",
        "bedrooms": "Beds",
        "days_on_market": "Days on market",
    }
)
st.dataframe(table_data, width="stretch", hide_index=True, height=360)
st.caption(
    "Synthetic data for platform demonstration. Anomalies indicate changes for investigation, not errors."
)
