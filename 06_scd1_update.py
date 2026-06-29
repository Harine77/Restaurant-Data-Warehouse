# ================================================================
#  06_scd1_update.py  —  STEP 6: SCD Type 1 Update
#
#  SCD1 = overwrite old value, no history kept
#  Columns:
#    dim_customer  : phone, email
#    dim_menu_item : price
#    dim_staff     : phone, salary
# ================================================================

import pandas as pd
import mysql.connector
from db_config import DB_CONFIG, DAY2_PATH

def conn():
    return mysql.connector.connect(**DB_CONFIG)

def scd1_customers(cx):
    print("\n  [SCD1] dim_customer  — phone, email")
    df = pd.read_csv(
        f"{DAY2_PATH}/customers_day2.csv",
        dtype={"customer_id": "str", "phone": "str"},
        keep_default_na=False
    )
    df = df.where(df != "", other=None)
    rc = cx.cursor(dictionary=True)
    wc = cx.cursor()
    changed = []

    for _, row in df.iterrows():
        rc.execute(
            "SELECT customer_key,phone,email FROM dim_customer "
            "WHERE customer_id=%s AND is_current=1",
            (row["customer_id"],)
        )
        ex = rc.fetchone()
        if not ex:
            continue

        p_chg = str(ex["phone"] or "") != str(row["phone"] or "")
        e_chg = str(ex["email"] or "") != str(row["email"] or "")

        if p_chg or e_chg:
            wc.execute(
                "UPDATE dim_customer SET phone=%s,email=%s "
                "WHERE customer_key=%s",
                (row["phone"], row["email"], ex["customer_key"])
            )
            changed.append(
                f"    ✓ {row['customer_id']}: "
                f"{'phone ' if p_chg else ''}{'email ' if e_chg else ''}updated"
            )

    cx.commit()
    rc.close()
    wc.close()

    for m in changed:
        print(m)
    print(f"    Total: {len(changed)} SCD1 customer updates")
    return len(changed)

def scd1_menu_items(cx):
    print("\n  [SCD1] dim_menu_item — price")
    df = pd.read_csv(
        f"{DAY2_PATH}/menu_items_day2.csv",
        dtype={"item_id": "str"},
        keep_default_na=False
    )
    rc = cx.cursor(dictionary=True)
    wc = cx.cursor()
    changed = []

    for _, row in df.iterrows():
        rc.execute(
            "SELECT item_key,item_name,price FROM dim_menu_item "
            "WHERE item_id=%s AND is_current=1",
            (row["item_id"],)
        )
        ex = rc.fetchone()
        if not ex:
            continue

        try:
            new_p = float(row["price"])
            old_p = float(ex["price"] or 0)
        except:
            continue

        if old_p != new_p:
            wc.execute(
                "UPDATE dim_menu_item SET price=%s WHERE item_key=%s",
                (new_p, ex["item_key"])
            )
            changed.append(
                f"    ✓ {row['item_id']} {ex['item_name']}: ₹{old_p} → ₹{new_p}"
            )

    cx.commit()
    rc.close()
    wc.close()

    for m in changed:
        print(m)
    print(f"    Total: {len(changed)} SCD1 price updates")
    return len(changed)

def scd1_staff(cx):
    print("\n  [SCD1] dim_staff     — phone, salary")
    df = pd.read_csv(
        f"{DAY2_PATH}/staff_day2.csv",
        dtype={"staff_id": "str", "phone": "str"},
        keep_default_na=False
    )
    df = df.where(df != "", other=None)
    rc = cx.cursor(dictionary=True)
    wc = cx.cursor()
    changed = []

    for _, row in df.iterrows():
        rc.execute(
            "SELECT staff_key,staff_name,phone,salary FROM dim_staff "
            "WHERE staff_id=%s AND is_current=1",
            (row["staff_id"],)
        )
        ex = rc.fetchone()
        if not ex:
            continue

        p_chg = str(ex["phone"] or "") != str(row["phone"] or "")
        try:
            s_chg = float(ex["salary"] or 0) != float(row["salary"] or 0)
        except:
            s_chg = False

        if p_chg or s_chg:
            wc.execute(
                "UPDATE dim_staff SET phone=%s,salary=%s "
                "WHERE staff_key=%s",
                (
                    row["phone"],
                    float(row["salary"]) if pd.notna(row.get("salary")) else None,
                    ex["staff_key"]
                )
            )
            changed.append(
                f"    ✓ {row['staff_id']} {ex['staff_name']}: "
                f"{'phone ' if p_chg else ''}{'salary ' if s_chg else ''}updated"
            )

    cx.commit()
    rc.close()
    wc.close()

    for m in changed:
        print(m)
    print(f"    Total: {len(changed)} SCD1 staff updates")
    return len(changed)

def main():
    print("="*55 + "\n  STEP 6 — SCD TYPE 1 (overwrite, no history)\n" + "="*55)
    cx = conn()
    print("  ✓ Connected")

    t = scd1_customers(cx) + scd1_menu_items(cx) + scd1_staff(cx)

    print(f"\n  TOTAL SCD1 changes applied: {t}")
    cx.close()
    print("\n" + "="*55 + "\n  SCD1 done.\n" + "="*55)

if __name__ == "__main__":
    main()