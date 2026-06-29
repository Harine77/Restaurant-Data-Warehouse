# ─────────────────────────────────────────────
# db_config.py 
# ─────────────────────────────────────────────
import os


def _load_db_config():
    try:
        import streamlit as st
        secrets = st.secrets.get("mysql", {})
    except Exception:
        secrets = {}

    return {
        "host": os.getenv("MYSQL_HOST", secrets.get("host", "localhost")),
        "user": os.getenv("MYSQL_USER", secrets.get("user", "root")),
        "password": os.getenv("MYSQL_PASSWORD", secrets.get("password", "")),
        "database": os.getenv("MYSQL_DATABASE", secrets.get("database", "restaurant_dw")),
    }


DB_CONFIG = _load_db_config()

DAY1_PATH = "source_data/day_1"
DAY2_PATH = "source_data/day_2"