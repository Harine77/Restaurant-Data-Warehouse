# ================================================================
#  08_incremental_load.py  —  STEP 8: Incremental Load (Day 2)
#
#  Only inserts BRAND NEW records not present in Day 1.
#  Uses etl_control watermark to detect new fact records.
#  Run AFTER 06_scd1_update.py and 07_scd2_update.py
# ================================================================

import pandas as pd, mysql.connector, datetime
from db_config import DB_CONFIG, DAY2_PATH

def conn(): return mysql.connector.connect(**DB_CONFIG)

def incr_customers(cx):
    print("\n  [INCREMENTAL] dim_customer — new customers")
    df = pd.read_csv(f"{DAY2_PATH}/customers_day2.csv",
                     dtype={"customer_id":"str","phone":"str"},
                     keep_default_na=False)
    df = df.where(df != "", other=None)
    ex = set(pd.read_sql("SELECT DISTINCT customer_id FROM dim_customer", cx)["customer_id"])
    new = df[~df["customer_id"].isin(ex)]
    cur = cx.cursor()
    for _, r in new.iterrows():
        cur.execute("""INSERT INTO dim_customer
            (customer_id,customer_name,phone,email,city,area,
             loyalty_tier,member_since,
             effective_start_date,effective_end_date,is_current)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
            (r["customer_id"], r["name"], r["phone"], r["email"],
             r["city"], r["area"], r["loyalty_tier"], r["member_since"],
             r["last_updated"]))
        print(f"    ✓ New customer: {r['customer_id']} — {r['name']}")
    cx.commit(); cur.close()
    print(f"    Total new customers: {len(new)}")
    return len(new)

def incr_menu_items(cx):
    print("\n  [INCREMENTAL] dim_menu_item — new items")
    df = pd.read_csv(f"{DAY2_PATH}/menu_items_day2.csv",
                     dtype={"item_id":"str"}, keep_default_na=False)
    ex = set(pd.read_sql("SELECT DISTINCT item_id FROM dim_menu_item", cx)["item_id"])
    new = df[~df["item_id"].isin(ex)]
    cur = cx.cursor()
    for _, r in new.iterrows():
        is_veg = 1 if str(r.get("is_veg","1")) in ["Yes","1"] else 0
        cur.execute("""INSERT INTO dim_menu_item
            (item_id,item_name,category,sub_category,price,
             is_veg,is_available,calories,prep_time_min,
             effective_start_date,effective_end_date,is_current)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
            (r["item_id"], r["item_name"], r["category"], r["sub_category"],
             float(r["price"]) if r["price"] not in [None,""] else None,
             is_veg, 1,
             int(r["calories"]) if r["calories"] not in [None,""] else None,
             int(r["prep_time_min"]) if r["prep_time_min"] not in [None,""] else None,
             r["last_updated"]))
        print(f"    ✓ New item: {r['item_id']} — {r['item_name']}")
    cx.commit(); cur.close()
    print(f"    Total new menu items: {len(new)}")
    return len(new)

def incr_staff(cx):
    print("\n  [INCREMENTAL] dim_staff — new staff")
    df = pd.read_csv(f"{DAY2_PATH}/staff_day2.csv",
                     dtype={"staff_id":"str","phone":"str"},
                     keep_default_na=False)
    df = df.where(df != "", other=None)
    ex = set(pd.read_sql("SELECT DISTINCT staff_id FROM dim_staff", cx)["staff_id"])
    new = df[~df["staff_id"].isin(ex)]
    cur = cx.cursor()
    for _, r in new.iterrows():
        cur.execute("""INSERT INTO dim_staff
            (staff_id,staff_name,phone,email,role,department,
             salary,join_date,shift,status,
             effective_start_date,effective_end_date,is_current)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
            (r["staff_id"], r["name"], r["phone"], r["email"],
             r["role"], r["department"],
             float(r["salary"]) if r.get("salary") not in [None,""] else None,
             r["join_date"], r["shift"], r["status"],
             r["last_updated"]))
        print(f"    ✓ New staff: {r['staff_id']} — {r['name']}")
    cx.commit(); cur.close()
    print(f"    Total new staff: {len(new)}")
    return len(new)

def incr_order_items(cx):
    print("\n  [INCREMENTAL] fact_order_items — new transactions")

    # watermark from etl_control
    ctl = pd.read_sql("""SELECT last_loaded_date FROM etl_control
                          WHERE source_name='order_items'""", cx)
    last_date = str(ctl.iloc[0,0]) if len(ctl) else "1900-01-01"
    print(f"    Watermark (last loaded date): {last_date}")

    # load Day2 files
    oi = pd.read_csv(f"{DAY2_PATH}/order_items_day2.csv",
                     dtype={"order_item_id":"str","order_id":"str","item_id":"str"})
    od = pd.read_csv(f"{DAY2_PATH}/orders_day2.csv",
                     dtype={"order_id":"str","customer_id":"str","staff_id":"str"})

    # only orders after watermark
    od = od[od["order_date"] > last_date]
    print(f"    New orders after watermark: {len(od)}")

    # skip already-loaded order_items
    ex_oi = set(pd.read_sql("SELECT order_item_id FROM fact_order_items", cx)["order_item_id"])
    oi = oi[~oi["order_item_id"].isin(ex_oi)]

    # only order_items belonging to new orders
    oi = oi[oi["order_id"].isin(set(od["order_id"]))]

    if len(oi) == 0:
        print("    No new order items to load.")
        return 0

    # ensure dim_date has entries for new dates
    cur = cx.cursor()
    for d_str in od["order_date"].unique():
        d  = datetime.datetime.strptime(str(d_str), "%Y-%m-%d")
        dk = int(d.strftime("%Y%m%d"))
        cur.execute("""INSERT IGNORE INTO dim_date
            (date_key,full_date,day_of_month,month_num,month_name,
             quarter,year,week_number,day_name,is_weekend)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (dk, d.date(), d.day, d.month, d.strftime("%B"),
             (d.month-1)//3+1, d.year,
             int(d.strftime("%W")), d.strftime("%A"),
             1 if d.weekday()>=5 else 0))
    cx.commit()

    # lookup maps (use is_current=1 to get latest surrogate keys)
    rc = cx.cursor(dictionary=True)
    rc.execute("SELECT customer_id,customer_key FROM dim_customer WHERE is_current=1")
    cust_map = {r["customer_id"]: r["customer_key"] for r in rc.fetchall()}

    rc.execute("SELECT staff_id,staff_key FROM dim_staff WHERE is_current=1")
    stf_map  = {r["staff_id"]:  r["staff_key"]  for r in rc.fetchall()}

    rc.execute("SELECT item_id,item_key FROM dim_menu_item WHERE is_current=1")
    item_map = {r["item_id"]:  r["item_key"]   for r in rc.fetchall()}

    ord_ctx = od.set_index("order_id")[
        ["customer_id","staff_id","order_date","order_type","payment_mode"]
    ].to_dict("index")

    loaded = skipped = 0
    for _, r in oi.iterrows():
        ctx = ord_ctx.get(r["order_id"])
        if not ctx:
            skipped += 1; continue

        ck = cust_map.get(ctx["customer_id"])
        sk = stf_map.get(ctx["staff_id"])
        ik = item_map.get(r["item_id"])

        if not ck or not sk or not ik:
            print(f"    SKIP {r['order_item_id']}: missing FK"); skipped+=1; continue

        date_key = int(str(ctx["order_date"]).replace("-",""))
        cur.execute("""INSERT IGNORE INTO fact_order_items
            (order_item_id,order_id,order_type,payment_mode,
             customer_key,staff_key,item_key,date_key,
             quantity,unit_price,discount,line_total)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r["order_item_id"], r["order_id"],
             ctx["order_type"], ctx["payment_mode"],
             ck, sk, ik, date_key,
             int(r["quantity"]), float(r["unit_price"]),
             float(r["discount"]), float(r["line_total"])))
        loaded += 1

    cx.commit()

    # update watermark
    new_max = od["order_date"].max()
    cur.execute("""INSERT INTO etl_control(source_name,last_loaded_date)
                   VALUES('order_items',%s)
                   ON DUPLICATE KEY UPDATE
                   last_loaded_date=%s, last_run_at=NOW()""",
                (new_max, new_max))
    cx.commit()
    rc.close(); cur.close()
    print(f"    ✓ {loaded} new order_items inserted  |  {skipped} skipped")
    print(f"    Watermark updated → {new_max}")
    return loaded

def main():
    print("="*55+"\n  STEP 8 — INCREMENTAL LOAD (new records only)\n"+"="*55)
    cx = conn(); print("  ✓ Connected")
    t  = incr_customers(cx) + incr_menu_items(cx)
    t += incr_staff(cx)     + incr_order_items(cx)
    print(f"\n  TOTAL new records inserted: {t}")
    cx.close()
    print("\n"+"="*55+"\n  Incremental load done. Run 09_aggregations.sql next.\n"+"="*55)

if __name__ == "__main__":
    main()