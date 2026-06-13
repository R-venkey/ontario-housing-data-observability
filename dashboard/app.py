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
from dashboard.power_bi_exports import build_export_tables, dataframe_to_csv_bytes
from modeling.price_model import estimate_price, train_price_model

ASSET_DIR = PROJECT_ROOT / "dashboard" / "assets"
PROPERTY_IMAGES = {
    "Detached": ASSET_DIR / "detached-house.png",
    "Semi-Detached": ASSET_DIR / "semi-detached-house.png",
    "Townhouse": ASSET_DIR / "townhouse.png",
    "Condo": ASSET_DIR / "condo.png",
}

CITY_COLORS = {
    "Toronto": "#0d9488",
    "Mississauga": "#7c3aed",
    "Brampton": "#ea580c",
    "Ottawa": "#16a34a",
    "Hamilton": "#e11d48",
    "Oshawa": "#2563eb",
}


@st.cache_data
def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    return load_local_data()


@st.cache_resource
def load_price_model(data: pd.DataFrame):
    return train_price_model(data)


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
        font=dict(color="#52606d", family="DM Sans, sans-serif"),
        title_font=dict(size=17, color="#14213d"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="#ffffff", font_color="#14213d"),
    )
    fig.update_xaxes(gridcolor="rgba(100,116,139,0.10)", linecolor="#dbe4ea")
    fig.update_yaxes(gridcolor="rgba(100,116,139,0.10)", linecolor="#dbe4ea")
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
        --ink: #14213d;
        --muted: #64748b;
        --panel: rgba(255, 255, 255, 0.94);
        --line: rgba(15, 118, 110, 0.13);
        --accent: #0f766e;
        --accent-soft: #e7f7f4;
    }

    .stApp {
        background:
            radial-gradient(circle at 88% 0%, rgba(253, 186, 116, 0.22), transparent 27%),
            radial-gradient(circle at 8% 22%, rgba(45, 212, 191, 0.13), transparent 26%),
            #f7faf9;
        color: var(--ink);
        font-family: "DM Sans", sans-serif;
    }

    h1, h2, h3, [data-testid="stMetricValue"] {
        font-family: "Space Grotesk", sans-serif !important;
        letter-spacing: -0.03em;
    }

    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.97);
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
        background:
            linear-gradient(120deg, rgba(255,255,255,0.98), rgba(234, 250, 246, 0.95));
        padding: 30px 34px;
        border-radius: 22px;
        margin-bottom: 22px;
        box-shadow: 0 22px 55px rgba(15, 118, 110, 0.09);
    }

    .eyebrow {
        color: var(--accent);
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
        color: #5f6f7f;
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
        box-shadow: 0 12px 32px rgba(31, 41, 55, 0.05);
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
        box-shadow: 0 12px 32px rgba(31, 41, 55, 0.045);
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
        color: #0f766e;
        line-height: 1;
    }

    .quality-label {
        color: var(--muted);
        margin-top: 8px;
    }

    .status-pill {
        display: inline-block;
        background: #e7f7f4;
        color: #0f766e;
        border: 1px solid rgba(15, 118, 110, 0.20);
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

    [data-testid="stDownloadButton"] button {
        width: 100%;
        min-height: 52px;
        border-radius: 12px;
        border: 1px solid rgba(15, 118, 110, 0.25);
        background: #edf9f6;
        color: #0f766e;
        font-weight: 700;
    }

    [data-testid="stDownloadButton"] button:hover {
        border-color: #0f766e;
        background: #dff5ef;
    }

    [data-testid="stImage"] img {
        border-radius: 16px;
        aspect-ratio: 3 / 2;
        object-fit: cover;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.96);
        border-color: var(--line);
        border-radius: 18px;
        box-shadow: 0 14px 35px rgba(31, 41, 55, 0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

silver, gold, quality, anomalies = load_dashboard_data()
price_model = load_price_model(silver)

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
        <div class="eyebrow">Ontario housing market</div>
        <h1>Find the market story<br/>behind every kind of home.</h1>
        <p>Compare prices, activity, and property types across six Ontario
        cities with trusted data behind every view.</p>
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

st.markdown('<div class="section-title">Explore by home type</div>', unsafe_allow_html=True)
property_summary = (
    filtered_silver.groupby("property_type", as_index=True)
    .agg(average_price=("sale_price", "mean"), sales=("record_id", "nunique"))
)
property_columns = st.columns(4)
for column, property_type in zip(property_columns, PROPERTY_IMAGES):
    with column:
        with st.container(border=True):
            st.image(
                str(PROPERTY_IMAGES[property_type]),
                caption=property_type,
                width="stretch",
            )
            if property_type in property_summary.index:
                property_row = property_summary.loc[property_type]
                st.markdown(f"### {property_type}")
                st.markdown(
                    f"**{currency(property_row['average_price'])}** average sale price"
                )
                st.caption(f"{int(property_row['sales']):,} sales in the selected period")
            else:
                st.markdown(f"### {property_type}")
                st.caption("No sales in the selected period")

st.markdown('<div class="section-title">Home value estimator</div>', unsafe_allow_html=True)
estimator_intro, estimator_form = st.columns([0.72, 1.28])
with estimator_intro:
    st.markdown("### Estimate a market price")
    st.write(
        "Enter a location and property profile to receive a model-based estimate "
        "trained on the synthetic Ontario transaction history."
    )
    st.metric("Validation MAE", currency(price_model.mean_absolute_error))
    st.caption(
        f"Held-out R²: {price_model.r2_score:.3f} · "
        f"{price_model.training_rows:,} training records"
    )
    st.info(
        "The street address is shown only as context in your session. This model "
        "does not geocode it or estimate block-level location effects."
    )

with estimator_form:
    with st.form("home_value_estimator"):
        address = st.text_input(
            "Street address",
            placeholder="Example: 123 Main Street",
        )
        location_col, type_col = st.columns(2)
        estimate_city = location_col.selectbox("City", all_cities)
        estimate_type = type_col.selectbox(
            "Property type",
            list(PROPERTY_IMAGES),
        )
        bedroom_col, market_col, date_col = st.columns(3)
        estimate_bedrooms = bedroom_col.number_input(
            "Bedrooms",
            min_value=1,
            max_value=8,
            value=3,
            step=1,
        )
        estimate_days = market_col.number_input(
            "Expected days on market",
            min_value=1,
            max_value=180,
            value=24,
            step=1,
        )
        estimate_date = date_col.date_input(
            "Valuation date",
            value=max_month,
        )
        submitted = st.form_submit_button(
            "Estimate home value",
            type="primary",
            width="stretch",
        )

    if submitted:
        estimate = estimate_price(
            price_model,
            city=estimate_city,
            property_type=estimate_type,
            bedrooms=int(estimate_bedrooms),
            days_on_market=int(estimate_days),
            valuation_date=pd.Timestamp(estimate_date),
        )
        estimate_label = address.strip() or f"{estimate_type} in {estimate_city}"
        st.success(f"Estimated market value for {estimate_label}")
        result_columns = st.columns(3)
        result_columns[0].metric(
            "Estimated price",
            currency(estimate.predicted_price),
        )
        result_columns[1].metric(
            "Lower range",
            currency(estimate.lower_bound),
        )
        result_columns[2].metric(
            "Upper range",
            currency(estimate.upper_bound),
        )
        st.caption(
            "The range uses the 80th percentile of held-out model errors. "
            "This is an educational estimate based on synthetic data, not an appraisal."
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

st.markdown('<div class="section-title">Download center</div>', unsafe_allow_html=True)
st.caption(
    "CSV downloads use the active city and reporting-period filters. "
    "The quality file describes the complete silver dataset."
)
download_tables = build_export_tables(
    filtered_silver,
    filtered_gold,
    quality,
    filtered_anomalies,
)
download_columns = st.columns(4)
download_columns[0].download_button(
    "Download transactions",
    dataframe_to_csv_bytes(download_tables["transactions"]),
    file_name="filtered_housing_transactions.csv",
    mime="text/csv",
    help=f"{len(download_tables['transactions']):,} filtered transaction rows.",
)
download_columns[1].download_button(
    "Download monthly KPIs",
    dataframe_to_csv_bytes(download_tables["monthly_kpis"]),
    file_name="filtered_monthly_city_kpis.csv",
    mime="text/csv",
    help=f"{len(download_tables['monthly_kpis']):,} filtered city-month rows.",
)
download_columns[2].download_button(
    "Download anomalies",
    dataframe_to_csv_bytes(download_tables["anomalies"]),
    file_name="filtered_market_anomalies.csv",
    mime="text/csv",
    help=f"{len(download_tables['anomalies']):,} filtered anomaly rows.",
)
download_columns[3].download_button(
    "Download quality checks",
    dataframe_to_csv_bytes(download_tables["quality_checks"]),
    file_name="quality_checks.csv",
    mime="text/csv",
    help="Pipeline-level quality controls and issue counts.",
)
