"""
dashboard/app.py
Streamlit Dashboard for IPO Analytics
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IPO Analytics Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DB engine ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine():
    url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER','ipo_user')}:{os.getenv('DB_PASSWORD','ipo_pass')}"
        f"@{os.getenv('DB_HOST','postgres')}:{os.getenv('DB_PORT','5432')}"
        f"/{os.getenv('DB_NAME','ipo_db')}"
    )
    return create_engine(url)


@st.cache_data(ttl=300)
def load_ipo_master() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM ipo_master ORDER BY open_date DESC", conn)
    return df


@st.cache_data(ttl=300)
def load_subscription() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            """
            SELECT m.ipo_name, m.open_date, s.qib, s.hni, s.rii, s.total_subscription
            FROM ipo_subscription s
            JOIN ipo_master m ON m.ipo_id = s.ipo_id
            ORDER BY m.open_date DESC
            """,
            conn,
        )
    return df


@st.cache_data(ttl=300)
def load_pipeline_log() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT * FROM pipeline_log ORDER BY created_at DESC LIMIT 100", conn
        )
    return df


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 📈 IPO Analytics")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "📋 Subscription Analytics", "🏆 Performance", "📅 Market Trends", "⚙️ Pipeline Log"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Data refreshes every 5 minutes")

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    df_master = load_ipo_master()
    df_sub    = load_subscription()
    df_log    = load_pipeline_log()
    data_ok   = True
except Exception as e:
    data_ok = False
    st.error(f"⚠️ Database connection failed: {e}")
    st.info("Make sure the PostgreSQL container is running and the pipeline has been executed at least once.")
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 – OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
if page == "📊 Overview":
    st.title("📈 IPO Analytics — Overview")
    st.markdown("---")

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    total_ipos      = len(df_master)
    total_funds     = df_master["issue_size"].sum()
    avg_listing_gain = df_master["listing_gain"].mean()
    positive_ipos   = (df_master["listing_gain"] > 0).sum()

    col1.metric("Total IPOs", f"{total_ipos:,}")
    col2.metric("Total Funds Raised", f"₹{total_funds:,.0f} Cr")
    col3.metric("Avg Listing Gain", f"{avg_listing_gain:.2f}%" if pd.notna(avg_listing_gain) else "N/A")
    col4.metric("IPOs with Positive Gain", f"{positive_ipos} / {total_ipos}")

    st.markdown("---")

    # Recent IPOs table
    st.subheader("🆕 Recent IPOs")
    cols_to_show = ["ipo_name", "open_date", "close_date", "issue_size",
                    "offer_price", "list_price", "listing_gain", "sector"]
    display_df = df_master[cols_to_show].head(20).copy()
    display_df.columns = ["IPO Name", "Open", "Close", "Issue Size (Cr)",
                          "Offer Price", "List Price", "Listing Gain %", "Sector"]

    def color_gain(val):
        if pd.isna(val):
            return ""
        color = "green" if val > 0 else "red"
        return f"color: {color}; font-weight: bold"

    st.dataframe(
        display_df.style.applymap(color_gain, subset=["Listing Gain %"]),
        use_container_width=True, height=400,
    )

    # Listing Gain Distribution
    st.subheader("📊 Listing Gain Distribution")
    fig = px.histogram(
        df_master.dropna(subset=["listing_gain"]),
        x="listing_gain", nbins=40,
        title="Distribution of Listing Gains (%)",
        labels={"listing_gain": "Listing Gain (%)"},
        color_discrete_sequence=["#4f8ef7"],
    )
    fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Break-even")
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 – SUBSCRIPTION ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📋 Subscription Analytics":
    st.title("📋 Subscription Analytics")
    st.markdown("---")

    if df_sub.empty:
        st.info("No subscription data available yet.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg QIB Subscription", f"{df_sub['qib'].mean():.1f}x")
        col2.metric("Avg HNI Subscription", f"{df_sub['hni'].mean():.1f}x")
        col3.metric("Avg RII Subscription", f"{df_sub['rii'].mean():.1f}x")

        st.markdown("---")

        # Bar chart: top subscribed IPOs
        st.subheader("🔝 Top 15 Most Subscribed IPOs (Total)")
        top15 = df_sub.nlargest(15, "total_subscription")
        fig = px.bar(
            top15, x="ipo_name", y="total_subscription",
            title="Top 15 IPOs by Total Subscription",
            labels={"total_subscription": "Total Subscription (x)", "ipo_name": ""},
            color="total_subscription", color_continuous_scale="Blues",
        )
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Grouped bar: QIB vs HNI vs RII
        st.subheader("📊 QIB / HNI / RII Breakdown (Recent 20 IPOs)")
        recent = df_sub.head(20).melt(
            id_vars="ipo_name", value_vars=["qib", "hni", "rii"],
            var_name="Category", value_name="Subscription (x)"
        )
        fig2 = px.bar(
            recent, x="ipo_name", y="Subscription (x)", color="Category",
            barmode="group", title="Subscription Breakdown by Category",
        )
        fig2.update_xaxes(tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 – PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🏆 Performance":
    st.title("🏆 IPO Performance Analytics")
    st.markdown("---")

    df_perf = df_master.dropna(subset=["listing_gain"])

    col1, col2 = st.columns(2)

    # Top Gainers
    with col1:
        st.subheader("🟢 Top 10 Gainers")
        gainers = df_perf.nlargest(10, "listing_gain")[["ipo_name", "listing_gain", "offer_price", "list_price"]]
        fig = px.bar(
            gainers, x="listing_gain", y="ipo_name", orientation="h",
            color="listing_gain", color_continuous_scale="Greens",
            labels={"listing_gain": "Listing Gain (%)", "ipo_name": ""},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Top Losers
    with col2:
        st.subheader("🔴 Top 10 Losers")
        losers = df_perf.nsmallest(10, "listing_gain")[["ipo_name", "listing_gain", "offer_price", "list_price"]]
        fig2 = px.bar(
            losers, x="listing_gain", y="ipo_name", orientation="h",
            color="listing_gain", color_continuous_scale="Reds_r",
            labels={"listing_gain": "Listing Gain (%)", "ipo_name": ""},
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Scatter: offer price vs listing gain
    st.subheader("💡 Offer Price vs Listing Gain")
    fig3 = px.scatter(
        df_perf, x="offer_price", y="listing_gain",
        hover_name="ipo_name", color="sector",
        title="Does Offer Price Correlate with Listing Gain?",
        labels={"offer_price": "Offer Price (₹)", "listing_gain": "Listing Gain (%)"},
    )
    fig3.add_hline(y=0, line_dash="dash", line_color="red")
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 – MARKET TRENDS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📅 Market Trends":
    st.title("📅 Market Trends")
    st.markdown("---")

    df_trend = df_master.copy()
    df_trend["year"] = pd.to_datetime(df_trend["open_date"], errors="coerce").dt.year

    yearly = (
        df_trend.groupby("year")
        .agg(total_ipos=("ipo_name", "count"),
             total_funds=("issue_size", "sum"),
             avg_gain=("listing_gain", "mean"))
        .reset_index()
        .dropna(subset=["year"])
    )
    yearly["year"] = yearly["year"].astype(int)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(yearly, x="year", y="total_ipos",
                     title="Number of IPOs per Year",
                     labels={"total_ipos": "IPO Count", "year": "Year"},
                     color_discrete_sequence=["#4f8ef7"])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = px.bar(yearly, x="year", y="total_funds",
                      title="Capital Raised per Year (₹ Cr)",
                      labels={"total_funds": "Funds (Cr)", "year": "Year"},
                      color_discrete_sequence=["#f7914f"])
        st.plotly_chart(fig2, use_container_width=True)

    # Avg listing gain per year
    fig3 = px.line(yearly, x="year", y="avg_gain",
                   title="Average Listing Gain per Year (%)",
                   markers=True,
                   labels={"avg_gain": "Avg Gain (%)", "year": "Year"})
    fig3.add_hline(y=0, line_dash="dash", line_color="red")
    st.plotly_chart(fig3, use_container_width=True)

    # Sector breakdown
    if "sector" in df_master.columns:
        st.subheader("🏭 IPOs by Sector")
        sector_counts = df_master["sector"].value_counts().reset_index()
        sector_counts.columns = ["Sector", "Count"]
        fig4 = px.pie(sector_counts.head(12), names="Sector", values="Count",
                      title="Sector Distribution of IPOs", hole=0.3)
        st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 – PIPELINE LOG
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⚙️ Pipeline Log":
    st.title("⚙️ Pipeline Execution Log")
    st.markdown("---")

    if df_log.empty:
        st.info("No pipeline runs recorded yet.")
    else:
        # Summary metrics
        total_runs    = len(df_log)
        success_runs  = (df_log["status"] == "success").sum()
        failed_runs   = (df_log["status"] == "failed").sum()
        avg_duration  = df_log["duration_sec"].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Runs", total_runs)
        col2.metric("Successful", success_runs)
        col3.metric("Failed", failed_runs)
        col4.metric("Avg Duration", f"{avg_duration:.1f}s" if pd.notna(avg_duration) else "N/A")

        st.markdown("---")
        st.subheader("📋 Recent Run Log")

        def highlight_status(val):
            if val == "success":
                return "background-color: #d4edda; color: #155724"
            elif val == "failed":
                return "background-color: #f8d7da; color: #721c24"
            return ""

        st.dataframe(
            df_log.style.applymap(highlight_status, subset=["status"]),
            use_container_width=True, height=400,
        )
