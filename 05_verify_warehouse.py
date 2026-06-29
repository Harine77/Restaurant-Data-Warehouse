# ================================================================
#  05_verify_warehouse.py  —  STEP 5: Verify after Day1 load
# ================================================================
import pandas as pd
import mysql.connector
from db_config import DB_CONFIG

def conn(): return mysql.connector.connect(**DB_CONFIG)

def main():
    print("="*60+"\n  STEP 5 — WAREHOUSE VERIFICATION (Day 1)\n"+"="*60)
    cx = conn()

    # ── row counts ────────────────────────────────────────────
    print("\n  --- ROW COUNTS ---")
    for tbl, sql in [
        ("dim_date",
         "SELECT COUNT(*) c, NULL cur FROM dim_date"),
        ("dim_customer",
         "SELECT COUNT(*) c, SUM(is_current) cur FROM dim_customer"),
        ("dim_menu_item",
         "SELECT COUNT(*) c, SUM(is_current) cur FROM dim_menu_item"),
        ("dim_staff",
         "SELECT COUNT(*) c, SUM(is_current) cur FROM dim_staff"),
        ("fact_order_items",
         "SELECT COUNT(*) c, NULL cur FROM fact_order_items"),
    ]:
        r = pd.read_sql(sql, cx).iloc[0]
        cur_info = f"  ({int(r['cur'])} current)" if r["cur"] is not None else ""
        print(f"    {tbl:<22} {int(r['c'])} rows{cur_info}")

    # ── revenue summary ───────────────────────────────────────
    print("\n  --- REVENUE SUMMARY ---")
    rev = pd.read_sql("""
        SELECT
            COUNT(DISTINCT order_id)          AS total_orders,
            SUM(line_total)                   AS gross_revenue,
            SUM(discount)                     AS total_discount,
            SUM(line_total) - SUM(discount)   AS net_revenue,
            ROUND(AVG(line_total),2)          AS avg_line_value
        FROM fact_order_items
    """, cx)
    print(rev.to_string(index=False))

    # ── top 5 dishes ──────────────────────────────────────────
    print("\n  --- TOP 5 DISHES BY REVENUE ---")
    print(pd.read_sql("""
        SELECT m.item_name, m.category,
               SUM(f.quantity)   AS qty_sold,
               SUM(f.line_total) AS revenue
        FROM fact_order_items f
        JOIN dim_menu_item m ON f.item_key = m.item_key
        WHERE m.is_current = 1
        GROUP BY m.item_name, m.category
        ORDER BY revenue DESC LIMIT 5
    """, cx).to_string(index=False))

    # ── top 5 customers ───────────────────────────────────────
    print("\n  --- TOP 5 CUSTOMERS BY SPEND ---")
    print(pd.read_sql("""
        SELECT c.customer_name, c.loyalty_tier,
               COUNT(DISTINCT f.order_id) AS orders,
               SUM(f.line_total)          AS total_spend
        FROM fact_order_items f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        WHERE c.is_current = 1
        GROUP BY c.customer_name, c.loyalty_tier
        ORDER BY total_spend DESC LIMIT 5
    """, cx).to_string(index=False))

    # ── orders by type ─────────────────────────────────────────
    print("\n  --- ORDERS BY TYPE ---")
    print(pd.read_sql("""
        SELECT order_type,
               COUNT(DISTINCT order_id) AS orders,
               SUM(line_total)          AS revenue
        FROM fact_order_items
        GROUP BY order_type
    """, cx).to_string(index=False))

    # ── FK integrity ──────────────────────────────────────────
    print("\n  --- FK INTEGRITY ---")
    for label, sql in [
        ("Orphan customer_key",
         "SELECT COUNT(*) n FROM fact_order_items f LEFT JOIN dim_customer c ON f.customer_key=c.customer_key WHERE c.customer_key IS NULL"),
        ("Orphan staff_key",
         "SELECT COUNT(*) n FROM fact_order_items f LEFT JOIN dim_staff s ON f.staff_key=s.staff_key WHERE s.staff_key IS NULL"),
        ("Orphan item_key",
         "SELECT COUNT(*) n FROM fact_order_items f LEFT JOIN dim_menu_item m ON f.item_key=m.item_key WHERE m.item_key IS NULL"),
        ("Orphan date_key",
         "SELECT COUNT(*) n FROM fact_order_items f LEFT JOIN dim_date d ON f.date_key=d.date_key WHERE d.date_key IS NULL"),
    ]:
        n = pd.read_sql(sql, cx).iloc[0,0]
        status = "✓ OK" if n == 0 else f"✗ {n} orphans"
        print(f"    {label:<22} {status}")

    # ── etl control ────────────────────────────────────────────
    print("\n  --- ETL CONTROL ---")
    print(pd.read_sql("SELECT * FROM etl_control", cx).to_string(index=False))

    cx.close()
    print("\n"+"="*60+"\n  Verification done. Run 06_scd1_update.py next.\n"+"="*60)

if __name__ == "__main__":
    main()