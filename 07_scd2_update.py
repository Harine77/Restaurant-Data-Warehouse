# ================================================================
#  07_scd2_update.py  —  STEP 7: SCD Type 2 Update
#
#  SCD2 = expire old row + insert new versioned row
#  Columns:
#    dim_customer  : city, loyalty_tier
#    dim_menu_item : category
#    dim_staff     : role
# ================================================================

import pandas as pd
import mysql.connector
from db_config import DB_CONFIG, DAY2_PATH

def conn(): return mysql.connector.connect(**DB_CONFIG)

def scd2_customers(cx):
    print("\n  [SCD2] dim_customer  — city, loyalty_tier")
    df = pd.read_csv(f"{DAY2_PATH}/customers_day2.csv",
                     dtype={"customer_id":"str","phone":"str"},
                     keep_default_na=False)
    df = df.where(df != "", other=None)
    rc = cx.cursor(dictionary=True); wc = cx.cursor()
    count = 0
    for _, row in df.iterrows():
        rc.execute("SELECT * FROM dim_customer "
                   "WHERE customer_id=%s AND is_current=1", (row["customer_id"],))
        ex = rc.fetchone()
        if not ex: continue
        c_chg = str(ex["city"] or "") != str(row["city"] or "")
        t_chg = str(ex["loyalty_tier"] or "") != str(row["loyalty_tier"] or "")
        if c_chg or t_chg:
            chg_date = row["last_updated"]
            # 1. expire old row
            wc.execute("""UPDATE dim_customer
                          SET is_current=0, effective_end_date=%s
                          WHERE customer_key=%s""",
                       (chg_date, ex["customer_key"]))
            # 2. insert new version
            wc.execute("""INSERT INTO dim_customer
                (customer_id,customer_name,phone,email,city,area,
                 loyalty_tier,member_since,
                 effective_start_date,effective_end_date,is_current)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
                (ex["customer_id"], ex["customer_name"],
                 ex["phone"], ex["email"],
                 row["city"], row["area"],          # new SCD2 values
                 row["loyalty_tier"],               # new SCD2 value
                 ex["member_since"], chg_date))
            print(f"    ✓ {ex['customer_id']} {ex['customer_name']}")
            if c_chg: print(f"        city          : {ex['city']} → {row['city']}")
            if t_chg: print(f"        loyalty_tier  : {ex['loyalty_tier']} → {row['loyalty_tier']}")
            count += 1
    cx.commit(); rc.close(); wc.close()
    print(f"    Total: {count} SCD2 customer versions created")
    return count

def scd2_menu_items(cx):
    print("\n  [SCD2] dim_menu_item — category")
    df = pd.read_csv(f"{DAY2_PATH}/menu_items_day2.csv",
                     dtype={"item_id":"str"}, keep_default_na=False)
    rc = cx.cursor(dictionary=True); wc = cx.cursor()
    count = 0
    for _, row in df.iterrows():
        rc.execute("SELECT * FROM dim_menu_item "
                   "WHERE item_id=%s AND is_current=1", (row["item_id"],))
        ex = rc.fetchone()
        if not ex: continue
        if str(ex["category"] or "") != str(row["category"] or ""):
            chg_date = row["last_updated"]
            wc.execute("""UPDATE dim_menu_item
                          SET is_current=0, effective_end_date=%s
                          WHERE item_key=%s""",
                       (chg_date, ex["item_key"]))
            is_veg = 1 if str(row.get("is_veg","1")) in ["Yes","1"] else 0
            wc.execute("""INSERT INTO dim_menu_item
                (item_id,item_name,category,sub_category,price,
                 is_veg,is_available,calories,prep_time_min,
                 effective_start_date,effective_end_date,is_current)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
                (ex["item_id"], ex["item_name"],
                 row["category"],                  # new SCD2 value
                 row["sub_category"],
                 ex["price"],                      # carry forward SCD1 price
                 is_veg, 1,
                 ex["calories"], ex["prep_time_min"],
                 chg_date))
            print(f"    ✓ {ex['item_id']} {ex['item_name']}: "
                  f"category {ex['category']} → {row['category']}")
            count += 1
    cx.commit(); rc.close(); wc.close()
    print(f"    Total: {count} SCD2 menu item versions created")
    return count

def scd2_staff(cx):
    print("\n  [SCD2] dim_staff     — role")
    df = pd.read_csv(f"{DAY2_PATH}/staff_day2.csv",
                     dtype={"staff_id":"str","phone":"str"},
                     keep_default_na=False)
    df = df.where(df != "", other=None)
    rc = cx.cursor(dictionary=True); wc = cx.cursor()
    count = 0
    for _, row in df.iterrows():
        rc.execute("SELECT * FROM dim_staff "
                   "WHERE staff_id=%s AND is_current=1", (row["staff_id"],))
        ex = rc.fetchone()
        if not ex: continue
        if str(ex["role"] or "") != str(row["role"] or ""):
            chg_date = row["last_updated"]
            wc.execute("""UPDATE dim_staff
                          SET is_current=0, effective_end_date=%s
                          WHERE staff_key=%s""",
                       (chg_date, ex["staff_key"]))
            wc.execute("""INSERT INTO dim_staff
                (staff_id,staff_name,phone,email,role,department,
                 salary,join_date,shift,status,
                 effective_start_date,effective_end_date,is_current)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,1)""",
                (ex["staff_id"], ex["staff_name"],
                 ex["phone"], ex["email"],
                 row["role"],                      # new SCD2 value
                 row["department"],
                 ex["salary"],                     # carry forward SCD1 salary
                 ex["join_date"], row["shift"], row["status"],
                 chg_date))
            print(f"    ✓ {ex['staff_id']} {ex['staff_name']}: "
                  f"role {ex['role']} → {row['role']}")
            count += 1
    cx.commit(); rc.close(); wc.close()
    print(f"    Total: {count} SCD2 staff versions created")
    return count

def main():
    print("="*55+"\n  STEP 7 — SCD TYPE 2 (versioned history)\n"+"="*55)
    cx = conn(); print("  ✓ Connected")
    t = scd2_customers(cx) + scd2_menu_items(cx) + scd2_staff(cx)
    print(f"\n  TOTAL SCD2 new versions created: {t}")
    cx.close()
    print("\n"+"="*55+"\n  SCD2 done. Run 08_incremental_load.py next.\n"+"="*55)

if __name__ == "__main__":
    main()
