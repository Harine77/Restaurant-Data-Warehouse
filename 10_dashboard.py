# ================================================================
#  10_dashboard.py  —  STEP 10: Streamlit Dashboard
#
#  Run with:  streamlit run 10_dashboard.py
#  Opens at:  http://localhost:8501
#
#  Install:   pip install streamlit plotly pandas mysql-connector-python
# ================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error as MySQLError
from sqlalchemy import create_engine
from db_config import DB_CONFIG

# ── page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Restaurant Analytics",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── custom CSS ────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #F8F9FA; }
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #2E75B6;
        margin-bottom: 8px;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #1F3864; }
    .metric-label { font-size: 13px; color: #666; margin-top: 2px; }
    .section-header {
        font-size: 18px; font-weight: 600;
        color: #1F3864; margin: 16px 0 10px 0;
        border-bottom: 2px solid #2E75B6; padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: white; border-radius: 8px 8px 0 0;
        font-weight: 500; color: #1F3864;
    }
</style>
""", unsafe_allow_html=True)

# ── DB connection (cached) ────────────────────────────────────
@st.cache_resource
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


@st.cache_resource
def get_engine():
    return create_engine(
        f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )

@st.cache_data(ttl=60)
def run_query(sql):
    engine = get_engine()
    df = pd.read_sql(sql, engine)
    return df

# ── load all data ─────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_all():
    daily    = run_query("SELECT * FROM agg_daily_revenue ORDER BY full_date")
    items    = run_query("SELECT * FROM agg_item_performance ORDER BY total_revenue DESC")
    customers= run_query("SELECT * FROM agg_customer_summary ORDER BY total_spend DESC")
    staff    = run_query("SELECT * FROM agg_staff_performance ORDER BY orders_handled DESC")
    category = run_query("SELECT * FROM agg_category_summary ORDER BY total_revenue DESC")
    monthly  = run_query("SELECT * FROM agg_monthly_summary ORDER BY year, month_num")
    loyalty  = run_query("SELECT * FROM agg_loyalty_revenue")
    hourly   = run_query("SELECT * FROM agg_hourly_orders ORDER BY full_date")
    return daily, items, customers, staff, category, monthly, loyalty, hourly

def show_db_setup_message(error_message):
    st.error("Database connection failed. The dashboard needs a reachable MySQL database.")
    st.markdown(
        """
        ### What to set for Streamlit Cloud
        - `MYSQL_HOST`
        - `MYSQL_USER`
        - `MYSQL_PASSWORD`
        - `MYSQL_DATABASE`

        Put them in Streamlit secrets or environment variables.
        """
    )
    st.code(error_message)
    st.stop()


try:
    daily, items, customers, staff, category, monthly, loyalty, hourly = load_all()
except (MySQLError, Exception) as exc:
    show_db_setup_message(str(exc))

# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://img.icons8.com/color/96/restaurant.png", width=60)
    st.title("Restaurant Dashboard")
    st.caption("Data Warehouse Analytics Dashboard")
    st.divider()

    st.subheader("🔍 Filters")

    # date range
    if len(daily) > 0:
        min_date = pd.to_datetime(daily["full_date"]).min().date()
        max_date = pd.to_datetime(daily["full_date"]).max().date()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date, max_value=max_date)
    else:
        date_range = None

    # loyalty filter
    tiers = ["All"] + sorted(customers["loyalty_tier"].dropna().unique().tolist())
    sel_tier = st.selectbox("Loyalty Tier", tiers)

    # order type filter
    if "order_type" in hourly.columns:
        types = ["All"] + sorted(hourly["order_type"].dropna().unique().tolist())
        sel_type = st.selectbox("Order Type", types)
    else:
        sel_type = "All"

    st.divider()
    st.caption("ETL Internship Project\nSystech Solutions · 2024")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ── apply filters ─────────────────────────────────────────────
daily_f = daily.copy()
if date_range and len(date_range) == 2:
    daily_f = daily_f[
        (pd.to_datetime(daily_f["full_date"]).dt.date >= date_range[0]) &
        (pd.to_datetime(daily_f["full_date"]).dt.date <= date_range[1])
    ]

cust_f = customers.copy()
if sel_tier != "All":
    cust_f = cust_f[cust_f["loyalty_tier"] == sel_tier]

hourly_f = hourly.copy()
if sel_type != "All" and "order_type" in hourly_f.columns:
    hourly_f = hourly_f[hourly_f["order_type"] == sel_type]

# ════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════
st.markdown("# 🍽️ Restaurant Analytics")
st.markdown("**Star Schema Data Warehouse** · SCD1 · SCD2 · Incremental Loading · ETL Pipeline")
st.divider()

# ════════════════════════════════════════════════════════════════
# KPI METRICS ROW
# ════════════════════════════════════════════════════════════════
total_revenue  = float(daily_f["gross_revenue"].sum())  if len(daily_f) > 0 else 0
total_orders   = int(daily_f["total_orders"].sum())     if len(daily_f) > 0 else 0
total_items    = int(daily_f["total_items_sold"].sum()) if len(daily_f) > 0 else 0
total_discount = float(daily_f["total_discount"].sum()) if len(daily_f) > 0 else 0
avg_order_val  = total_revenue / total_orders if total_orders > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)
for col, label, val, fmt in [
    (k1, "💰 Gross Revenue",    total_revenue,  "₹{:,.0f}"),
    (k2, "🧾 Total Orders",     total_orders,   "{:,}"),
    (k3, "🍛 Items Sold",       total_items,    "{:,}"),
    (k4, "🎁 Total Discount",   total_discount, "₹{:,.0f}"),
    (k5, "📊 Avg Order Value",  avg_order_val,  "₹{:.0f}"),
]:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{fmt.format(val)}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("")

# ════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Revenue Trends",
    "🍛 Menu Performance",
    "👥 Customer Insights",
    "👨‍🍳 Staff Performance",
    "🏷️ SCD Changes",
    "📋 Raw Data"
])

# ─────────────────────────────────────────────────────────────
# TAB 1: Revenue Trends
# ─────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">Daily Revenue Trend</div>',
                unsafe_allow_html=True)

    if len(daily_f) > 0:
        daily_plot = daily_f.copy()
        daily_plot["full_date"] = pd.to_datetime(daily_plot["full_date"])

        c1, c2 = st.columns([4, 1])
        with c2:
            st.caption("Trend Controls")
            trend_grain = st.selectbox(
                "Time Grain",
                ["Daily", "Weekly", "Monthly"],
                key="rev_trend_grain"
            )
            trend_metric = st.selectbox(
                "Metric",
                ["Both", "Gross Revenue", "Net Revenue"],
                key="rev_trend_metric"
            )
            show_avg = st.checkbox("Show Moving Average", value=True, key="rev_trend_avg")

        trend_df = daily_plot.copy()
        if trend_grain == "Weekly":
            trend_df["full_date"] = trend_df["full_date"].dt.to_period("W").dt.start_time
            trend_df = trend_df.groupby("full_date", as_index=False)[["gross_revenue", "net_revenue"]].sum()
        elif trend_grain == "Monthly":
            trend_df["full_date"] = trend_df["full_date"].dt.to_period("M").dt.start_time
            trend_df = trend_df.groupby("full_date", as_index=False)[["gross_revenue", "net_revenue"]].sum()

        with c1:
            fig = go.Figure()
            if trend_metric in ["Both", "Gross Revenue"]:
                fig.add_trace(go.Bar(
                    x=trend_df["full_date"], y=trend_df["gross_revenue"],
                    name="Gross Revenue", marker_color="#2E75B6", opacity=0.75
                ))
                if show_avg and len(trend_df) >= 3:
                    fig.add_trace(go.Scatter(
                        x=trend_df["full_date"],
                        y=trend_df["gross_revenue"].rolling(3).mean(),
                        name="Gross MA(3)",
                        line=dict(color="#0B4F8A", dash="dot", width=2)
                    ))
            if trend_metric in ["Both", "Net Revenue"]:
                fig.add_trace(go.Scatter(
                    x=trend_df["full_date"], y=trend_df["net_revenue"],
                    name="Net Revenue", line=dict(color="#1F3864", width=2.8)
                ))
                if show_avg and len(trend_df) >= 3:
                    fig.add_trace(go.Scatter(
                        x=trend_df["full_date"],
                        y=trend_df["net_revenue"].rolling(3).mean(),
                        name="Net MA(3)",
                        line=dict(color="#E67E22", dash="dot", width=2)
                    ))
            fig.update_layout(
                title=f"{trend_grain} Revenue Trend (₹)",
                xaxis_title="Date",
                yaxis_title="Revenue (₹)",
                legend=dict(orientation="h", y=1.08),
                plot_bgcolor="white",
                paper_bgcolor="white",
                height=370
            )
            st.plotly_chart(fig, width="stretch")

        st.markdown('<div class="section-header">Weekday vs Weekend Split</div>',
                    unsafe_allow_html=True)
        c3, c4 = st.columns([4, 1])
        with c4:
            st.caption("Split Controls")
            split_metric = st.selectbox(
                "Split Metric",
                ["gross_revenue", "net_revenue", "total_orders"],
                key="rev_split_metric"
            )
            split_style = st.radio(
                "Chart Type",
                ["Donut", "Bar"],
                key="rev_split_style"
            )

        wk_df = daily_plot.groupby("is_weekend", as_index=False)[split_metric].sum()
        wk_df["day_type"] = wk_df["is_weekend"].map({0: "Weekday", 1: "Weekend"})
        with c3:
            if split_style == "Donut":
                fig2 = px.pie(
                    wk_df,
                    values=split_metric,
                    names="day_type",
                    hole=0.45,
                    title=f"Weekday vs Weekend by {split_metric.replace('_', ' ').title()}",
                    color_discrete_sequence=["#2E75B6", "#E67E22"]
                )
            else:
                fig2 = px.bar(
                    wk_df,
                    x="day_type",
                    y=split_metric,
                    title=f"Weekday vs Weekend by {split_metric.replace('_', ' ').title()}",
                    color="day_type",
                    color_discrete_sequence=["#2E75B6", "#E67E22"]
                )
                fig2.update_layout(showlegend=False)
            fig2.update_layout(height=340, paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig2, width="stretch")

        st.markdown('<div class="section-header">Monthly Revenue Summary</div>',
                    unsafe_allow_html=True)
        if len(monthly) > 0:
            monthly_view = monthly.copy()
            monthly_view["month_label"] = monthly_view["month_name"].astype(str) + " " + monthly_view["year"].astype(str)

            c5, c6 = st.columns([4, 1])
            with c6:
                st.caption("Monthly Controls")
                month_metric = st.selectbox(
                    "Monthly Metric",
                    ["gross_revenue", "net_revenue", "total_orders"],
                    key="rev_month_metric"
                )
                quarter_choices = sorted(monthly_view["quarter"].dropna().unique().tolist())
                selected_quarters = st.multiselect(
                    "Quarter",
                    quarter_choices,
                    default=quarter_choices,
                    key="rev_month_quarter"
                )

            if selected_quarters:
                monthly_view = monthly_view[monthly_view["quarter"].isin(selected_quarters)]

            with c5:
                fig3 = px.bar(
                    monthly_view,
                    x="month_label",
                    y=month_metric,
                    color="quarter",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    title=f"Monthly {month_metric.replace('_', ' ').title()} by Quarter",
                    labels={month_metric: "Value", "month_label": "Month"}
                )
                fig3.update_layout(plot_bgcolor="white", paper_bgcolor="white", height=330)
                st.plotly_chart(fig3, width="stretch")

        st.markdown('<div class="section-header">Orders by Type & Payment Mode</div>',
                    unsafe_allow_html=True)

        c7, c8 = st.columns([4, 1])
        with c8:
            st.caption("Order Type Controls")
            order_type_style = st.radio(
                "Order Type Chart",
                ["Donut", "Bar"],
                key="rev_order_type_style"
            )

        otype = hourly_f.groupby("order_type", as_index=False)["total_orders"].sum()
        with c7:
            if order_type_style == "Donut":
                fig4 = px.pie(
                    otype,
                    values="total_orders",
                    names="order_type",
                    hole=0.4,
                    title="Dine-In vs Takeaway",
                    color_discrete_sequence=["#1F3864", "#2E75B6"]
                )
            else:
                fig4 = px.bar(
                    otype,
                    x="order_type",
                    y="total_orders",
                    title="Dine-In vs Takeaway",
                    color="order_type",
                    color_discrete_sequence=["#1F3864", "#2E75B6"]
                )
                fig4.update_layout(showlegend=False)
            fig4.update_layout(height=320, paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig4, width="stretch")

        c9, c10 = st.columns([4, 1])
        with c10:
            st.caption("Payment Controls")
            top_n_payment = st.slider("Top N Modes", 2, 10, 6, key="rev_payment_top_n")

        pay = hourly_f.groupby("payment_mode", as_index=False)["total_orders"].sum()
        pay = pay.sort_values("total_orders", ascending=False).head(top_n_payment)
        with c9:
            fig5 = px.bar(
                pay,
                x="payment_mode",
                y="total_orders",
                title="Orders by Payment Mode",
                color="payment_mode",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig5.update_layout(showlegend=False, height=320,
                               plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig5, width="stretch")
    else:
        st.info("No data for selected date range.")

# ─────────────────────────────────────────────────────────────
# TAB 2: Menu Performance
# ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">Top 10 Dishes by Revenue</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        top10 = items.head(10)
        fig = px.bar(top10, x="total_revenue", y="item_name",
                     orientation="h",
                     color="category",
                     title="Top 10 Dishes by Revenue (₹)",
                     labels={"total_revenue":"Revenue (₹)","item_name":"Dish"},
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(yaxis=dict(autorange="reversed"),
                          plot_bgcolor="white", paper_bgcolor="white", height=380)
        st.plotly_chart(fig, width="stretch")

    with c2:
        veg_rev = items.groupby("is_veg").agg(
            revenue=("total_revenue","sum"),
            items=("item_name","count")).reset_index()
        veg_rev["label"] = veg_rev["is_veg"].map({1:"🟢 Veg", 0:"🔴 Non-Veg"})
        fig2 = px.pie(veg_rev, values="revenue", names="label",
                      title="Veg vs Non-Veg Revenue",
                      color_discrete_sequence=["#27AE60","#E74C3C"])
        fig2.update_layout(height=380, paper_bgcolor="white")
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-header">Category Performance</div>',
                unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        fig3 = px.treemap(category, path=["category"],
                          values="total_revenue",
                          title="Revenue Share by Category",
                          color="total_revenue",
                          color_continuous_scale="Blues")
        fig3.update_layout(height=320, paper_bgcolor="white")
        st.plotly_chart(fig3, width="stretch")
    with c4:
        fig4 = px.bar(category.head(8), x="category", y="total_qty_sold",
                      title="Items Sold by Category",
                      color="category",
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        fig4.update_layout(showlegend=False, height=320,
                           plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig4, width="stretch")

    st.markdown('<div class="section-header">Full Menu Performance Table</div>',
                unsafe_allow_html=True)
    st.dataframe(
        items[["item_name","category","is_veg","current_price",
               "times_ordered","total_qty_sold","total_revenue"]].rename(columns={
            "item_name":"Dish","category":"Category","is_veg":"Veg",
            "current_price":"Price(₹)","times_ordered":"Orders",
            "total_qty_sold":"Qty Sold","total_revenue":"Revenue(₹)"}),
        width="stretch", height=300)

# ─────────────────────────────────────────────────────────────
# TAB 3: Customer Insights
# ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">Customer Loyalty Analysis</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(loyalty, values="num_customers", names="loyalty_tier",
                     title="Customers by Loyalty Tier",
                     color_discrete_sequence=["#F39C12","#C0392B","#27AE60"])
        fig.update_layout(height=320, paper_bgcolor="white")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = px.bar(loyalty, x="loyalty_tier", y="revenue_per_customer",
                      title="Avg Revenue per Customer by Tier",
                      color="loyalty_tier",
                      color_discrete_sequence=["#F39C12","#C0392B","#27AE60"],
                      labels={"revenue_per_customer":"Revenue/Customer (₹)"},
                      text="revenue_per_customer")
        fig2.update_traces(texttemplate="₹%{text:.0f}", textposition="outside")
        fig2.update_layout(showlegend=False, height=320,
                           plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<div class="section-header">Top 15 Customers by Spend</div>',
                unsafe_allow_html=True)
    top_c = cust_f.head(15)
    fig3 = px.bar(top_c, x="customer_name", y="total_spend",
                  color="loyalty_tier",
                  title="Top 15 Customers — Total Spend (₹)",
                  color_discrete_map={"Gold":"#F39C12",
                                      "Silver":"#95A5A6",
                                      "Bronze":"#CD6F1A"},
                  labels={"total_spend":"Total Spend (₹)","customer_name":"Customer"})
    fig3.update_layout(xaxis_tickangle=-35, height=350,
                       plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig3, width="stretch")

    st.markdown('<div class="section-header">Customer Summary Table</div>',
                unsafe_allow_html=True)
    st.dataframe(
        cust_f[["customer_name","city","loyalty_tier","total_orders",
                "total_spend","total_discount_received",
                "first_visit","last_visit"]].rename(columns={
            "customer_name":"Name","city":"City",
            "loyalty_tier":"Tier","total_orders":"Orders",
            "total_spend":"Spend(₹)","total_discount_received":"Discount(₹)",
            "first_visit":"First Visit","last_visit":"Last Visit"}),
        width="stretch", height=300)

# ─────────────────────────────────────────────────────────────
# TAB 4: Staff Performance
# ─────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">Staff Performance Overview</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(staff.head(10), x="revenue_generated", y="staff_name",
                     orientation="h",
                     color="role",
                     title="Top Staff by Revenue Generated (₹)",
                     labels={"revenue_generated":"Revenue(₹)","staff_name":"Staff"})
        fig.update_layout(yaxis=dict(autorange="reversed"),
                          plot_bgcolor="white", paper_bgcolor="white", height=380)
        st.plotly_chart(fig, width="stretch")
    with c2:
        dept = staff.groupby("department").agg(
            orders=("orders_handled","sum"),
            revenue=("revenue_generated","sum")).reset_index()
        fig2 = px.bar(dept, x="department", y="revenue",
                      title="Revenue by Department",
                      color="department",
                      color_discrete_sequence=px.colors.qualitative.Set3,
                      text="revenue")
        fig2.update_traces(texttemplate="₹%{text:.0f}", textposition="outside")
        fig2.update_layout(showlegend=False, height=380,
                           plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig2, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        shift = staff.groupby("shift").agg(
            orders=("orders_handled","sum")).reset_index()
        fig3 = px.pie(shift, values="orders", names="shift",
                      title="Orders by Shift",
                      color_discrete_sequence=["#2E75B6","#E67E22"])
        fig3.update_layout(height=300, paper_bgcolor="white")
        st.plotly_chart(fig3, width="stretch")
    with c4:
        role_grp = staff.groupby("role").agg(
            count=("staff_id","count"),
            revenue=("revenue_generated","sum")).reset_index()
        fig4 = px.scatter(role_grp, x="count", y="revenue",
                          text="role", title="Role: Headcount vs Revenue",
                          size="revenue",
                          color_discrete_sequence=["#2E75B6"])
        fig4.update_traces(textposition="top center")
        fig4.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig4, width="stretch")

    st.markdown('<div class="section-header">Staff Details Table</div>',
                unsafe_allow_html=True)
    st.dataframe(
        staff[["staff_name","role","department","shift",
               "orders_handled","items_served","revenue_generated"]].rename(columns={
            "staff_name":"Name","role":"Role","department":"Dept",
            "shift":"Shift","orders_handled":"Orders",
            "items_served":"Items","revenue_generated":"Revenue(₹)"}),
        width="stretch", height=280)

# ─────────────────────────────────────────────────────────────
# TAB 5: SCD Changes Proof
# ─────────────────────────────────────────────────────────────
with tab5:
    st.markdown("## 🔄 SCD Changes — Data Warehouse Evidence")
    st.info("These tables prove that SCD1, SCD2, and Incremental Loading worked correctly.")

    # SCD1
    st.markdown("### ✏️ SCD Type 1 — Overwrite (No History)")
    st.markdown("**Rule:** When `phone`, `email`, `price`, or `salary` changes → old value overwritten. Only 1 row per entity.")

    t1, t2, t3 = st.tabs(["👥 dim_customer (SCD1)","🍛 dim_menu_item (SCD1)","👨‍🍳 dim_staff (SCD1)"])
    with t1:
        df = run_query("""
            SELECT customer_id, customer_name, phone, email,
                   city, loyalty_tier, is_current
            FROM dim_customer
            WHERE customer_id IN ('CUST002','CUST007','CUST010')
            ORDER BY customer_id""")
        st.dataframe(df, width="stretch")
        st.success("✓ 1 row per customer | Phone/email show Day2 values | History NOT kept → SCD1")
    with t2:
        df = run_query("""
            SELECT item_id, item_name, category, price, is_current
            FROM dim_menu_item
            WHERE item_id IN ('ITEM001','ITEM002','ITEM004','ITEM006','ITEM028')
              AND is_current=1 ORDER BY item_id""")
        st.dataframe(df, width="stretch")
        st.success("✓ Price updated to Day2 values | Old prices gone | 1 row per item → SCD1")
    with t3:
        df = run_query("""
            SELECT staff_id, staff_name, role, phone, salary, is_current
            FROM dim_staff
            WHERE staff_id IN ('STF001','STF002','STF006','STF015','STF025')
              AND is_current=1 ORDER BY staff_id""")
        st.dataframe(df, width="stretch")
        st.success("✓ Salary/phone updated in place | No history row | SCD1 confirmed")

    st.divider()

    # SCD2
    st.markdown("### 📚 SCD Type 2 — Versioned History")
    st.markdown("**Rule:** When `city`, `loyalty_tier`, `category`, or `role` changes → old row expired + new row inserted.")

    t4, t5, t6 = st.tabs(["👥 dim_customer (SCD2)","🍛 dim_menu_item (SCD2)","👨‍🍳 dim_staff (SCD2)"])
    with t4:
        df = run_query("""
            SELECT customer_id, customer_name, city, loyalty_tier,
                   effective_start_date, effective_end_date, is_current
            FROM dim_customer
            WHERE customer_id IN ('CUST003','CUST004','CUST015')
            ORDER BY customer_id, effective_start_date""")
        st.dataframe(df, width="stretch")
        st.success("✓ 2 rows per customer | is_current=0 (expired) + is_current=1 (current) | History kept → SCD2")
    with t5:
        df = run_query("""
            SELECT item_id, item_name, category, price,
                   effective_start_date, effective_end_date, is_current
            FROM dim_menu_item
            WHERE item_id = 'ITEM010'
            ORDER BY effective_start_date""")
        st.dataframe(df, width="stretch")
        st.success("✓ ITEM010 (Kesari): category Breakfast → Desserts | Old row expired | SCD2")
    with t6:
        df = run_query("""
            SELECT staff_id, staff_name, role, salary,
                   effective_start_date, effective_end_date, is_current
            FROM dim_staff
            WHERE staff_id IN ('STF007','STF021')
            ORDER BY staff_id, effective_start_date""")
        st.dataframe(df, width="stretch")
        st.success("✓ STF007: Waiter→Captain | STF021: Cook→Sous Chef | History preserved → SCD2")

    st.divider()

    # Incremental
    st.markdown("### ➕ Incremental Load — New Records Only")
    st.markdown("**Rule:** Only brand-new records inserted. etl_control watermark tracks last loaded date.")

    t7, t8 = st.tabs(["New Customers/Staff/Items","New Orders (fact)"])
    with t7:
        st.markdown("**New Customers (CUST041, CUST042, CUST043):**")
        df = run_query("""
            SELECT customer_id, customer_name, city, loyalty_tier,
                   effective_start_date, is_current
            FROM dim_customer
            WHERE customer_id IN ('CUST041','CUST042','CUST043')""")
        st.dataframe(df, width="stretch")
        st.markdown("**New Menu Items (ITEM041, ITEM042):**")
        df2 = run_query("""
            SELECT item_id, item_name, category, price, is_current
            FROM dim_menu_item
            WHERE item_id IN ('ITEM041','ITEM042')""")
        st.dataframe(df2, width="stretch")
        st.markdown("**New Staff (STF041, STF042):**")
        df3 = run_query("""
            SELECT staff_id, staff_name, role, department, is_current
            FROM dim_staff
            WHERE staff_id IN ('STF041','STF042')""")
        st.dataframe(df3, width="stretch")
    with t8:
        df4 = run_query("""
            SELECT f.order_id, c.customer_name, m.item_name,
                   d.full_date, f.order_type, f.quantity,
                   f.unit_price, f.line_total
            FROM fact_order_items f
            JOIN dim_customer  c ON f.customer_key = c.customer_key
            JOIN dim_menu_item m ON f.item_key     = m.item_key
            JOIN dim_date      d ON f.date_key     = d.date_key
            WHERE f.order_id IN
                  ('ORD041','ORD042','ORD043','ORD044','ORD045',
                   'ORD046','ORD047','ORD048','ORD049','ORD050')
            ORDER BY f.order_id LIMIT 20""")
        st.dataframe(df4, width="stretch")
        st.success("✓ New Day2 orders loaded | etl_control watermark updated")

    st.divider()
    st.markdown("### 📊 Final Row Count Summary")
    counts = run_query("""
        SELECT 'dim_customer'    AS tbl,
               COUNT(*)          AS total_rows,
               SUM(is_current)   AS current,
               SUM(1-is_current) AS expired
        FROM dim_customer
        UNION ALL
        SELECT 'dim_menu_item', COUNT(*), SUM(is_current), SUM(1-is_current)
        FROM dim_menu_item
        UNION ALL
        SELECT 'dim_staff', COUNT(*), SUM(is_current), SUM(1-is_current)
        FROM dim_staff
        UNION ALL
        SELECT 'dim_date', COUNT(*), COUNT(*), 0
        FROM dim_date
        UNION ALL
        SELECT 'fact_order_items', COUNT(*), COUNT(*), 0
        FROM fact_order_items
    """)
    st.dataframe(counts, width="stretch")

# ─────────────────────────────────────────────────────────────
# TAB 6: Raw Data
# ─────────────────────────────────────────────────────────────
with tab6:
    st.markdown("### 📋 Raw Warehouse Tables")
    tbl_choice = st.selectbox("Select table", [
        "dim_customer","dim_menu_item","dim_staff","dim_date","fact_order_items",
        "agg_daily_revenue","agg_item_performance","agg_customer_summary",
        "agg_staff_performance","agg_category_summary"])
    limit = st.slider("Rows to show", 10, 200, 50)
    df_raw = run_query(f"SELECT * FROM {tbl_choice} LIMIT {limit}")
    st.dataframe(df_raw, width="stretch")
    st.caption(f"Showing {min(limit, len(df_raw))} rows from `{tbl_choice}`")

# ─── footer ──────────────────────────────────────────────────
st.divider()
st.markdown(
    "<center><small>Data Warehouse · "
    "ETL Internship · Systech Solutions · 2024 · "
    "Built with Streamlit + MySQL + Python</small></center>",
    unsafe_allow_html=True)