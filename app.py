import streamlit as st
import pandas as pd
import sqlite3
import json
import math
import os
from datetime import datetime

# ================== 基本設定 ==================
st.set_page_config(page_title="阿杜羽球", page_icon="🏸", layout="centered")
st.title("🏸 阿杜羽球")

DB_DIR = os.path.expanduser("~/.badminton")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "badminton_pro.db")

# ================== DB 初始化 ==================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        revenue INTEGER,
        expense INTEGER,
        profit INTEGER,
        note TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================== config ==================
def load_config():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT value FROM config WHERE key='wallet_balance'")
    row = c.fetchone()
    wallet = int(row[0]) if row else 0

    c.execute("SELECT value FROM config WHERE key='ball_types'")
    row = c.fetchone()

    if row:
        ball_types = json.loads(row[0])
    else:
        ball_types = [
            {"name": "RSL No.4", "tube_price": 450, "count": 12},
            {"name": "勝利比賽級", "tube_price": 540, "count": 12}
        ]

    conn.close()
    return wallet, ball_types

def save_config(wallet, ball_types):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config VALUES ('wallet_balance', ?)", (str(int(wallet)),))
    c.execute("INSERT OR REPLACE INTO config VALUES ('ball_types', ?)", (json.dumps(ball_types),))
    conn.commit()
    conn.close()

def add_history(date, revenue, expense, profit, note):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO history (date, revenue, expense, profit, note)
        VALUES (?, ?, ?, ?, ?)
    """, (date, int(revenue), int(expense), int(profit), note))
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM history ORDER BY id DESC", conn)
    conn.close()
    return df

# ================== session init ==================
if "wallet" not in st.session_state:
    w, b = load_config()
    st.session_state.wallet = w
    st.session_state.ball_types = b

if "check_groups" not in st.session_state:
    st.session_state.check_groups = []

# ================== 球種 ==================
st.sidebar.header("💰 錢包")
st.sidebar.metric("餘額", st.session_state.wallet)

# ================== 分頁 ==================
tab1, tab2, tab3 = st.tabs(["📌 開團", "👥 收款", "📊 歷史"])

# ================== TAB 1 ==================
with tab1:
    st.header("場地費")

    rate = st.number_input("每小時", min_value=0, value=150, step=10)

    hours1 = st.number_input("場地1 小時", min_value=0, value=0, step=1)
    hours2 = st.number_input("場地2 小時", min_value=0, value=0, step=1)

    total_court = rate * int(hours1) + rate * int(hours2)

    st.write("場地費：", total_court)

# ================== TAB 2 ==================
with tab2:
    st.header("收款名單")

    text = st.text_area("貼名單", height=120)

    price = st.number_input("單價", min_value=0, value=250, step=10)

    if st.button("生成名單"):
        st.session_state.check_groups = [
            {"name": x.strip(), "price": price, "checked": False}
            for x in text.split("\n") if x.strip()
        ]

    st.divider()

    total = 0

    for i, p in enumerate(st.session_state.check_groups):
        c1, c2, c3, c4 = st.columns([0.6, 6, 2, 1])

        with c1:
            checked = st.checkbox("", value=p["checked"], key=f"c{i}")
            st.session_state.check_groups[i]["checked"] = checked

        with c2:
            if checked:
                st.write(f"~~{p['name']}~~")
            else:
                st.write(p["name"])

        with c3:
            st.write(f"${p['price']}")

        with c4:
            if st.button("✏️", key=f"e{i}"):
                st.session_state[f"edit{i}"] = True
            if st.button("🗑️", key=f"d{i}"):
                st.session_state.check_groups.pop(i)
                st.rerun()

        if st.session_state.get(f"edit{i}"):
            new_name = st.text_input("修改", p["name"], key=f"n{i}")
            if st.button("儲存", key=f"s{i}"):
                st.session_state.check_groups[i]["name"] = new_name
                st.session_state[f"edit{i}"] = False
                st.rerun()

        if checked:
            total += p["price"]

    st.write("總收款：", total)

# ================== TAB 3 ==================
with tab3:
    st.header("歷史")

    df = load_history()
    st.dataframe(df, use_container_width=True)

    if st.button("測試結算"):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        add_history(now, 1000, 500, 500, "demo")
        st.success("已新增")
        st.rerun()
