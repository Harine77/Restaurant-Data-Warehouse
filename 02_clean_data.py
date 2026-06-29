# ================================================================
#  02_clean_data.py
#  STEP 2 — Clean and standardise all Day1 source files
#  Writes cleaned versions to source_data/cleaned/ folder
# ================================================================

import pandas as pd
import os
from db_config import DAY1_PATH

CLEAN_PATH = "source_data/cleaned"
os.makedirs(CLEAN_PATH, exist_ok=True)

# ── helper: fix date format DD-MM-YYYY → YYYY-MM-DD ──────────
def fix_date(val):
    if pd.isnull(val) or val == "":
        return None
    val = str(val).strip()
    if len(val) == 10 and val[4] == "-":
        return val                        # already correct
    if len(val) == 10 and val[2] == "-":
        p = val.split("-")
        return f"{p[2]}-{p[1]}-{p[0]}"  # flip DD-MM-YYYY
    return val

# ─────────────────────────────────────────────────────────────
def clean_customers():
    print("\n  Cleaning customers...")
    df = pd.read_csv(f"{DAY1_PATH}/customers_day1.csv",
                     dtype={"customer_id": str, "phone": str},
                     keep_default_na=False)
    df = df.where(df != "", other=None)

    before = len(df)
    # 1. remove duplicates — keep row with most filled columns
    df["_filled"] = df.notna().sum(axis=1)
    df = df.sort_values("_filled", ascending=False)
    df = df.drop_duplicates(subset="customer_id", keep="first")
    df = df.drop(columns=["_filled"])
    print(f"    Dedup: {before} → {len(df)} rows")

    # 2. standardise text
    df["name"]          = df["name"].str.strip().fillna("Unknown")
    df["city"]          = df["city"].str.strip().str.title()
    df["area"]          = df["area"].str.strip().str.title()
    df["loyalty_tier"]  = df["loyalty_tier"].str.strip()

    # 3. fix dates
    df["member_since"]  = df["member_since"].apply(fix_date)
    df["last_updated"]  = df["last_updated"].apply(fix_date)

    # 4. phone / email → None if blank
    df["phone"] = df["phone"].replace("", None)
    df["email"] = df["email"].replace("", None)

    df.to_csv(f"{CLEAN_PATH}/customers_clean.csv", index=False)
    print(f"    Saved: {len(df)} clean rows")

# ─────────────────────────────────────────────────────────────
def clean_menu_items():
    print("\n  Cleaning menu_items...")
    df = pd.read_csv(f"{DAY1_PATH}/menu_items_day1.csv",
                     dtype={"item_id": str},
                     keep_default_na=False)
    df = df.where(df != "", other=None)

    before = len(df)
    df = df.drop_duplicates(subset="item_id", keep="first")
    print(f"    Dedup: {before} → {len(df)} rows")

    df["item_name"]  = df["item_name"].str.strip()
    df["category"]   = df["category"].str.strip().str.title()
    df["sub_category"] = df["sub_category"].str.strip().str.title()

    # cast numeric columns
    df["price"]          = pd.to_numeric(df["price"],    errors="coerce")
    df["calories"]       = pd.to_numeric(df["calories"], errors="coerce")
    df["prep_time_min"]  = pd.to_numeric(df["prep_time_min"], errors="coerce")

    # is_veg Yes/No → 1/0
    df["is_veg"]       = df["is_veg"].map({"Yes": 1, "No": 0}).fillna(0).astype(int)
    df["is_available"] = pd.to_numeric(df["is_available"], errors="coerce").fillna(1).astype(int)

    df["last_updated"] = df["last_updated"].apply(fix_date)

    df.to_csv(f"{CLEAN_PATH}/menu_items_clean.csv", index=False)
    print(f"    Saved: {len(df)} clean rows")

# ─────────────────────────────────────────────────────────────
def clean_staff():
    print("\n  Cleaning staff...")
    df = pd.read_csv(f"{DAY1_PATH}/staff_day1.csv",
                     dtype={"staff_id": str, "phone": str},
                     keep_default_na=False)
    df = df.where(df != "", other=None)

    before = len(df)
    df = df.drop_duplicates(subset="staff_id", keep="first")
    print(f"    Dedup: {before} → {len(df)} rows")

    df["name"]       = df["name"].str.strip()
    df["role"]       = df["role"].str.strip().str.title()
    df["department"] = df["department"].str.strip().str.title()
    df["shift"]      = df["shift"].str.strip().str.title()
    df["status"]     = df["status"].str.strip().str.title()

    df["salary"]     = pd.to_numeric(df["salary"], errors="coerce")
    df["join_date"]  = df["join_date"].apply(fix_date)
    df["last_updated"] = df["last_updated"].apply(fix_date)

    df.to_csv(f"{CLEAN_PATH}/staff_clean.csv", index=False)
    print(f"    Saved: {len(df)} clean rows")

# ─────────────────────────────────────────────────────────────
def clean_orders():
    print("\n  Cleaning orders...")
    df = pd.read_csv(f"{DAY1_PATH}/orders_day1.csv",
                     dtype={"order_id": str, "customer_id": str,
                            "staff_id": str},
                     keep_default_na=False)
    df = df.where(df != "", other=None)

    before = len(df)
    df = df.drop_duplicates(subset="order_id", keep="first")
    print(f"    Dedup: {before} → {len(df)} rows")

    df["order_type"]     = df["order_type"].str.strip().str.title()
    df["payment_mode"]   = df["payment_mode"].str.strip().str.title()
    df["payment_status"] = df["payment_status"].str.strip().str.title()

    df["total_amount"]   = pd.to_numeric(df["total_amount"], errors="coerce")
    df["discount"]       = pd.to_numeric(df["discount"],     errors="coerce").fillna(0)
    df["net_amount"]     = pd.to_numeric(df["net_amount"],   errors="coerce")
    df["num_items"]      = pd.to_numeric(df["num_items"],    errors="coerce")

    df["order_date"]   = df["order_date"].apply(fix_date)
    df["last_updated"] = df["last_updated"].apply(fix_date)

    df.to_csv(f"{CLEAN_PATH}/orders_clean.csv", index=False)
    print(f"    Saved: {len(df)} clean rows")

# ─────────────────────────────────────────────────────────────
def clean_order_items():
    print("\n  Cleaning order_items...")
    df = pd.read_csv(f"{DAY1_PATH}/order_items_day1.csv",
                     dtype={"order_item_id": str, "order_id": str,
                            "item_id": str},
                     keep_default_na=False)
    df = df.where(df != "", other=None)

    before = len(df)
    df = df.drop_duplicates(subset="order_item_id", keep="first")
    print(f"    Dedup: {before} → {len(df)} rows")

    df["quantity"]   = pd.to_numeric(df["quantity"],   errors="coerce").fillna(1).astype(int)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["discount"]   = pd.to_numeric(df["discount"],   errors="coerce").fillna(0)
    df["line_total"] = pd.to_numeric(df["line_total"], errors="coerce")
    df["last_updated"] = df["last_updated"].apply(fix_date)

    df.to_csv(f"{CLEAN_PATH}/order_items_clean.csv", index=False)
    print(f"    Saved: {len(df)} clean rows")

# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  STEP 2 — DATA CLEANING")
    print("=" * 55)
    clean_customers()
    clean_menu_items()
    clean_staff()
    clean_orders()
    clean_order_items()
    print("\n" + "=" * 55)
    print("  Cleaning done.")
    print("=" * 55)

if __name__ == "__main__":
    main()