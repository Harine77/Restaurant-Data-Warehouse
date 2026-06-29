# ================================================================
#  01_profile_data.py
#  STEP 1 — Profile all 5 Day1 source files
#  Output: prints a detailed quality report to terminal
# ================================================================

import pandas as pd
import os
from db_config import DAY1_PATH

def profile_file(filepath, name):
    print(f"\n{'='*60}")
    print(f"  FILE: {name}")
    print(f"{'='*60}")

    df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
    df = df.where(df != "", other=None)

    print(f"  Rows          : {len(df)}")
    print(f"  Columns       : {len(df.columns)}")
    print(f"  Column names  : {list(df.columns)}")

    print(f"\n  --- NULL / MISSING counts ---")
    for col in df.columns:
        nulls = df[col].isna().sum()
        if nulls > 0:
            print(f"    {col:<30} {nulls} missing")

    print(f"\n  --- DUPLICATE rows ---")
    dupes = df.duplicated().sum()
    print(f"    Total duplicate rows: {dupes}")

    print(f"\n  --- UNIQUE values per key column ---")
    for col in df.columns:
        if col.endswith("_id"):
            uniq = df[col].nunique()
            total = len(df)
            print(f"    {col:<30} {uniq} unique out of {total} rows"
                  + (" ← DUPLICATES EXIST" if uniq < total else ""))

    print(f"\n  --- SAMPLE (first 3 rows) ---")
    print(df.head(3).to_string(index=False))

def main():
    print("\n" + "="*60)
    print("  STEP 1 — DATA PROFILING REPORT")
    print("  Source: Day 1 files")
    print("="*60)

    files = {
        "customers":   "customers_day1.csv",
        "menu_items":  "menu_items_day1.csv",
        "staff":       "staff_day1.csv",
        "orders":      "orders_day1.csv",
        "order_items": "order_items_day1.csv",
    }

    for name, fname in files.items():
        path = os.path.join(DAY1_PATH, fname)
        profile_file(path, fname)

    print("\n" + "="*60)
    print("  Profiling complete.")
    print("="*60)

if __name__ == "__main__":
    main()