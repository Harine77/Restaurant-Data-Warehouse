# ================================================================
#  04_initial_load_day1.py  —  STEP 4: Initial Load (Day 1)
#  Loads cleaned data into:
#    dim_date, dim_customer, dim_menu_item, dim_staff, fact_order_items
#  Database: restaurant_dw (your schema)
# ================================================================

import pandas as pd, mysql.connector, datetime
from db_config import DB_CONFIG

CLEAN = "source_data/cleaned"

def conn(): return mysql.connector.connect(**DB_CONFIG)

# ── dim_date ──────────────────────────────────────────────────
def load_dim_date(cx):
    print("\n  Loading dim_date...")
    df = pd.read_csv(f"{CLEAN}/orders_clean.csv", dtype=str)
    dates = sorted(set(pd.to_datetime(df["order_date"].dropna()).dt.date))
    cur = cx.cursor()
    n = 0
    for d in dates:
        dt  = datetime.datetime(d.year, d.month, d.day)
        key = int(dt.strftime("%Y%m%d"))
        cur.execute("""
            INSERT IGNORE INTO dim_date
              (date_key,full_date,day_of_month,month_num,month_name,
               quarter,year,week_number,day_name,is_weekend)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (key, d, d.day, d.month, dt.strftime("%B"),
             (d.month-1)//3+1, d.year,
             int(dt.strftime("%W")), dt.strftime("%A"),
             1 if dt.weekday()>=5 else 0))
        n += 1
    cx.commit(); cur.close()
    print(f"    ✓ {n} date rows inserted")

# ── dim_customer ──────────────────────────────────────────────
def load_dim_customer(cx):
    print("\n  Loading dim_customer...")
    df = pd.read_csv(f"{CLEAN}/customers_clean.csv",
                     dtype={"customer_id":"str","phone":"str"})
    cur = cx.cursor()
    for _, r in df.iterrows():
        cur.execute("""
            INSERT INTO dim_customer
              (customer_id,customer_name,phone,email,city,area,
               loyalty_tier,member_since,
               effective_start_date,effective_end_date,is_current)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
            (r.customer_id, r["name"],
             r.phone if pd.notna(r.phone) else None,
             r.email if pd.notna(r.email) else None,
             r.city,  r.area, r.loyalty_tier,
             r.member_since if pd.notna(r.member_since) else None,
             r.last_updated))
    cx.commit(); cur.close()
    print(f"    ✓ {len(df)} customers inserted")

# ── dim_menu_item ─────────────────────────────────────────────
def load_dim_menu_item(cx):
    print("\n  Loading dim_menu_item...")
    df = pd.read_csv(f"{CLEAN}/menu_items_clean.csv", dtype={"item_id":"str"})
    cur = cx.cursor()
    for _, r in df.iterrows():
        cur.execute("""
            INSERT INTO dim_menu_item
              (item_id,item_name,category,sub_category,price,
               is_veg,is_available,calories,prep_time_min,
               effective_start_date,effective_end_date,is_current)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
            (r.item_id, r.item_name, r.category, r.sub_category,
             float(r.price)        if pd.notna(r.price)        else None,
             int(r.is_veg), int(r.is_available),
             int(r.calories)       if pd.notna(r.calories)       else None,
             int(r.prep_time_min)  if pd.notna(r.prep_time_min)  else None,
             r.last_updated))
    cx.commit(); cur.close()
    print(f"    ✓ {len(df)} menu items inserted")

# ── dim_staff ─────────────────────────────────────────────────
def load_dim_staff(cx):
    print("\n  Loading dim_staff...")
    df = pd.read_csv(f"{CLEAN}/staff_clean.csv",
                     dtype={"staff_id":"str","phone":"str"})
    cur = cx.cursor()
    for _, r in df.iterrows():
        cur.execute("""
            INSERT INTO dim_staff
              (staff_id,staff_name,phone,email,role,department,
               salary,join_date,shift,status,
               effective_start_date,effective_end_date,is_current)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
            (
    r["staff_id"],
    r["name"],
    r["phone"] if pd.notna(r["phone"]) else None,
    r["email"] if pd.notna(r["email"]) else None,
    r["role"],
    r["department"],
    float(r["salary"]) if pd.notna(r["salary"]) else None,
    r["join_date"] if pd.notna(r["join_date"]) else None,
    r["shift"],          # ← fixed
    r["status"],
    r["last_updated"]
))
    cx.commit(); cur.close()
    print(f"    ✓ {len(df)} staff inserted")

# ── fact_order_items ──────────────────────────────────────────
def load_fact_order_items(cx):
    print("\n  Loading fact_order_items...")

    oi = pd.read_csv(f"{CLEAN}/order_items_clean.csv",
                     dtype={"order_item_id":"str","order_id":"str","item_id":"str"})
    od = pd.read_csv(f"{CLEAN}/orders_clean.csv",
                     dtype={"order_id":"str","customer_id":"str","staff_id":"str"})

    # build lookup maps
    cur = cx.cursor(dictionary=True)

    cur.execute("SELECT customer_id, customer_key FROM dim_customer WHERE is_current=1")
    cust_map = {r["customer_id"]: r["customer_key"] for r in cur.fetchall()}

    cur.execute("SELECT staff_id, staff_key FROM dim_staff WHERE is_current=1")
    stf_map  = {r["staff_id"]:  r["staff_key"]  for r in cur.fetchall()}

    cur.execute("SELECT item_id, item_key FROM dim_menu_item WHERE is_current=1")
    item_map = {r["item_id"]:   r["item_key"]   for r in cur.fetchall()}

    # order context lookup  (order_id → customer_id, staff_id, date, order_type, payment_mode)
    ord_ctx = od.set_index("order_id")[
        ["customer_id","staff_id","order_date","order_type","payment_mode"]
    ].to_dict("index")

    wcur = cx.cursor()
    loaded = skipped = 0

    for _, r in oi.iterrows():
        ctx = ord_ctx.get(r.order_id)
        if not ctx:
            print(f"    SKIP {r.order_item_id}: order not found"); skipped+=1; continue

        ck = cust_map.get(ctx["customer_id"])
        sk = stf_map.get(ctx["staff_id"])
        ik = item_map.get(r.item_id)

        if not ck or not sk or not ik:
            print(f"    SKIP {r.order_item_id}: missing FK "
                  f"(cust={ck}, staff={sk}, item={ik})"); skipped+=1; continue

        date_key = int(str(ctx["order_date"]).replace("-",""))

        wcur.execute("""
            INSERT IGNORE INTO fact_order_items
              (order_item_id,order_id,order_type,payment_mode,
               customer_key,staff_key,item_key,date_key,
               quantity,unit_price,discount,line_total)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r.order_item_id, r.order_id,
             ctx["order_type"], ctx["payment_mode"],
             ck, sk, ik, date_key,
             int(r.quantity), float(r.unit_price),
             float(r.discount), float(r.line_total)))
        loaded += 1

    cx.commit()

    # update etl_control watermark
    max_date = od["order_date"].max()
    wcur.execute("""
        INSERT INTO etl_control(source_name,last_loaded_date)
        VALUES('order_items',%s)
        ON DUPLICATE KEY UPDATE last_loaded_date=%s, last_run_at=NOW()
    """, (max_date, max_date))
    cx.commit()

    cur.close(); wcur.close()
    print(f"    ✓ {loaded} rows inserted  |  {skipped} skipped")
    print(f"    etl_control watermark → {max_date}")

# ─────────────────────────────────────────────────────────────
def main():
    print("="*55+"\n  STEP 4 — INITIAL LOAD (DAY 1)\n"+"="*55)
    cx = conn()
    print("  ✓ Connected to restaurant_dw")
    load_dim_date(cx)
    load_dim_customer(cx)
    load_dim_menu_item(cx)
    load_dim_staff(cx)
    load_fact_order_items(cx)
    cx.close()
    print("\n"+"="*55+"\n  Day1 load complete. Run 05_verify_warehouse.py next.\n"+"="*55)

if __name__ == "__main__":
    main()