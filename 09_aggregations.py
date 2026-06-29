# ================================================================
#  09_aggregations.py  —  STEP 9: Create Aggregation Tables
#  Builds summary tables from fact_order_items for fast dashboard queries
# ================================================================

import pandas as pd
import mysql.connector
from db_config import DB_CONFIG

def conn(): return mysql.connector.connect(**DB_CONFIG)

def create_agg_tables(cx):
    cur = cx.cursor()

    # ── AGG 1: Daily Revenue ─────────────────────────────────
    print("\n  Creating agg_daily_revenue...")
    cur.execute("DROP TABLE IF EXISTS agg_daily_revenue")
    cur.execute("""
        CREATE TABLE agg_daily_revenue AS
        SELECT
            d.date_key,
            d.full_date,
            d.day_name,
            d.month_name,
            d.month_num,
            d.quarter,
            d.year,
            d.is_weekend,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            SUM(f.quantity)                 AS total_items_sold,
            SUM(f.line_total)               AS gross_revenue,
            SUM(f.discount)                 AS total_discount,
            SUM(f.line_total - f.discount)  AS net_revenue,
            ROUND(AVG(f.line_total), 2)     AS avg_line_value
        FROM fact_order_items f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY
            d.date_key, d.full_date, d.day_name,
            d.month_name, d.month_num, d.quarter,
            d.year, d.is_weekend
        ORDER BY d.full_date
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_daily_revenue", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 2: Item Performance ───────────────────────────────
    print("\n  Creating agg_item_performance...")
    cur.execute("DROP TABLE IF EXISTS agg_item_performance")
    cur.execute("""
        CREATE TABLE agg_item_performance AS
        SELECT
            m.item_id,
            m.item_name,
            m.category,
            m.sub_category,
            m.is_veg,
            m.price                         AS current_price,
            COUNT(DISTINCT f.order_id)      AS times_ordered,
            SUM(f.quantity)                 AS total_qty_sold,
            SUM(f.line_total)               AS total_revenue,
            SUM(f.discount)                 AS total_discount_given,
            ROUND(AVG(f.quantity), 2)       AS avg_qty_per_order,
            ROUND(AVG(f.line_total), 2)     AS avg_revenue_per_order
        FROM fact_order_items f
        JOIN dim_menu_item m ON f.item_key = m.item_key
        WHERE m.is_current = 1
        GROUP BY
            m.item_id, m.item_name, m.category,
            m.sub_category, m.is_veg, m.price
        ORDER BY total_revenue DESC
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_item_performance", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 3: Customer Summary ───────────────────────────────
    print("\n  Creating agg_customer_summary...")
    cur.execute("DROP TABLE IF EXISTS agg_customer_summary")
    cur.execute("""
        CREATE TABLE agg_customer_summary AS
        SELECT
            c.customer_id,
            c.customer_name,
            c.city,
            c.loyalty_tier,
            c.member_since,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            SUM(f.quantity)                 AS total_items_bought,
            SUM(f.line_total)               AS total_spend,
            SUM(f.discount)                 AS total_discount_received,
            ROUND(AVG(f.line_total), 2)     AS avg_spend_per_item,
            MIN(d.full_date)                AS first_visit,
            MAX(d.full_date)                AS last_visit
        FROM fact_order_items f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_date     d ON f.date_key     = d.date_key
        WHERE c.is_current = 1
        GROUP BY
            c.customer_id, c.customer_name, c.city,
            c.loyalty_tier, c.member_since
        ORDER BY total_spend DESC
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_customer_summary", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 4: Staff Performance ──────────────────────────────
    print("\n  Creating agg_staff_performance...")
    cur.execute("DROP TABLE IF EXISTS agg_staff_performance")
    cur.execute("""
        CREATE TABLE agg_staff_performance AS
        SELECT
            s.staff_id,
            s.staff_name,
            s.role,
            s.department,
            s.shift,
            COUNT(DISTINCT f.order_id)      AS orders_handled,
            SUM(f.quantity)                 AS items_served,
            SUM(f.line_total)               AS revenue_generated,
            ROUND(AVG(f.line_total), 2)     AS avg_per_item
        FROM fact_order_items f
        JOIN dim_staff s ON f.staff_key = s.staff_key
        WHERE s.is_current = 1
        GROUP BY
            s.staff_id, s.staff_name, s.role,
            s.department, s.shift
        ORDER BY revenue_generated DESC
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_staff_performance", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 5: Category Summary ───────────────────────────────
    print("\n  Creating agg_category_summary...")
    cur.execute("DROP TABLE IF EXISTS agg_category_summary")
    cur.execute("""
        CREATE TABLE agg_category_summary AS
        SELECT
            m.category,
            m.is_veg,
            COUNT(DISTINCT m.item_id)       AS num_items,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            SUM(f.quantity)                 AS total_qty_sold,
            SUM(f.line_total)               AS total_revenue,
            ROUND(AVG(f.line_total), 2)     AS avg_revenue_per_line
        FROM fact_order_items f
        JOIN dim_menu_item m ON f.item_key = m.item_key
        WHERE m.is_current = 1
        GROUP BY m.category, m.is_veg
        ORDER BY total_revenue DESC
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_category_summary", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 6: Monthly Summary ────────────────────────────────
    print("\n  Creating agg_monthly_summary...")
    cur.execute("DROP TABLE IF EXISTS agg_monthly_summary")
    cur.execute("""
        CREATE TABLE agg_monthly_summary AS
        SELECT
            d.year,
            d.month_num,
            d.month_name,
            d.quarter,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            SUM(f.quantity)                 AS total_items_sold,
            SUM(f.line_total)               AS gross_revenue,
            SUM(f.discount)                 AS total_discount,
            SUM(f.line_total - f.discount)  AS net_revenue,
            COUNT(DISTINCT f.customer_key)  AS unique_customers
        FROM fact_order_items f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.month_num, d.month_name, d.quarter
        ORDER BY d.year, d.month_num
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_monthly_summary", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 7: Hourly Footfall (peak hours) ──────────────────
    print("\n  Creating agg_hourly_orders...")
    cur.execute("DROP TABLE IF EXISTS agg_hourly_orders")
    # We derive hour from order_id pattern using orders source
    # Since we store order_type in fact, group by order_type and date
    cur.execute("""
        CREATE TABLE agg_hourly_orders AS
        SELECT
            d.full_date,
            d.day_name,
            f.order_type,
            f.payment_mode,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            SUM(f.line_total)               AS revenue
        FROM fact_order_items f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.full_date, d.day_name, f.order_type, f.payment_mode
        ORDER BY d.full_date
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_hourly_orders", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    # ── AGG 8: Loyalty Tier Revenue ───────────────────────────
    print("\n  Creating agg_loyalty_revenue...")
    cur.execute("DROP TABLE IF EXISTS agg_loyalty_revenue")
    cur.execute("""
        CREATE TABLE agg_loyalty_revenue AS
        SELECT
            c.loyalty_tier,
            COUNT(DISTINCT c.customer_id)   AS num_customers,
            COUNT(DISTINCT f.order_id)      AS total_orders,
            SUM(f.line_total)               AS total_revenue,
            ROUND(AVG(f.line_total),2)      AS avg_spend_per_item,
            ROUND(SUM(f.line_total) /
                  NULLIF(COUNT(DISTINCT c.customer_id),0), 2)
                                            AS revenue_per_customer
        FROM fact_order_items f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        WHERE c.is_current = 1
        GROUP BY c.loyalty_tier
        ORDER BY total_revenue DESC
    """)
    cx.commit()
    n = pd.read_sql("SELECT COUNT(*) n FROM agg_loyalty_revenue", cx).iloc[0,0]
    print(f"    ✓ {n} rows created")

    cur.close()

def verify_agg(cx):
    print("\n  --- AGGREGATION VERIFICATION ---")
    aggs = ["agg_daily_revenue","agg_item_performance",
            "agg_customer_summary","agg_staff_performance",
            "agg_category_summary","agg_monthly_summary",
            "agg_hourly_orders","agg_loyalty_revenue"]
    for a in aggs:
        n = pd.read_sql(f"SELECT COUNT(*) n FROM {a}", cx).iloc[0,0]
        print(f"    {a:<30} {n} rows")

def main():
    print("="*55+"\n  STEP 9 — AGGREGATIONS\n"+"="*55)
    cx = conn()
    print("  ✓ Connected to restaurant_dw")
    create_agg_tables(cx)
    verify_agg(cx)
    cx.close()
    print("\n"+"="*55)
    print("  Aggregations done. Run 10_screenshot_scd.py next.")
    print("="*55)

if __name__ == "__main__":
    main()