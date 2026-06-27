import streamlit as st
import re
import pandas as pd
import sqlite3
import json
import math
import os
from datetime import datetime

st.set_page_config(page_title="阿杜羽球", page_icon="🏸", layout="centered")
st.title("🏸 阿杜羽球")

# 資料庫路徑
DB_DIR = os.path.expanduser("~/.badminton")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "badminton_pro.db")

# ==================== 資料庫核心 ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, revenue REAL, expense REAL, profit REAL, note TEXT)')
    conn.commit()
    conn.close()

def load_config():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key='wallet_balance'")
    row = cursor.fetchone()
    wallet = int(float(row[0])) if row else 0
    cursor.execute("SELECT value FROM config WHERE key='ball_types'")
    row = cursor.fetchone()
    ball_types = json.loads(row[0]) if row else [{"name": "RSL No.4", "tube_price": 450.0, "count": 12}, {"name": "勝利比賽級", "tube_price": 540.0, "count": 12}]
    conn.close()
    return wallet, ball_types

def save_config(wallet, ball_types):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('wallet_balance', ?)", (str(int(wallet)),))
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('ball_types', ?)", (json.dumps(ball_types),))
    conn.commit()
    conn.close()

def save_today_draft(draft_data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('today_draft', ?)", (json.dumps(draft_data),))
    conn.commit()
    conn.close()

def load_today_draft():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key='today_draft'")
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row and row[0] else None

def add_history_record(date, revenue, expense, profit, note):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (date, revenue, expense, profit, note) VALUES (?, ?, ?, ?, ?)", (date, int(revenue), int(expense), int(profit), note))
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id as 編號, date as 日期, CAST(revenue AS INT) as 總收入, CAST(expense AS INT) as 總支出, CAST(profit AS INT) as 總利潤, note as 備註 FROM history ORDER BY id DESC", conn)
    conn.close()
    return df

init_db()

if "wallet_balance" not in st.session_state:
    w_bal, b_types = load_config()
    st.session_state.wallet_balance = int(w_bal)
    st.session_state.ball_types = b_types

draft = load_today_draft() or {
    "court_rate_1": 150, "court_hours_1": 0, "court_rate_2": 250, "court_hours_2": 0,
    "ball_selectors_count": 1, "ball_selections": [{"name": "", "count": 0}],
    "revenue_selectors_count": 1, "revenue_selections": [{"type": "250", "custom": 100, "count": 0}],
    "check_groups": [], "input_blocks_count": 1
}

def sync_state_to_draft():
    current_draft = {
        "court_rate_1": st.session_state.get("c_rate_1", 150),
        "court_hours_1": st.session_state.get("c_hours_1", 0),
        "court_rate_2": st.session_state.get("c_rate_2", 250),
        "court_hours_2": st.session_state.get("c_hours_2", 0),
        "ball_selectors_count": st.session_state.get("ball_selectors_count", 1),
        "ball_selections": [{"name": st.session_state.get(f"sel_ball_{i}", ""), "count": st.session_state.get(f"sel_count_{i}", 0)} for i in range(st.session_state.get("ball_selectors_count", 1))],
        "revenue_selectors_count": st.session_state.get("revenue_selectors_count", 1),
        "revenue_selections": [{"type": st.session_state.get(f"rev_type_{i}", "250"), "custom": st.session_state.get(f"rev_custom_{i}", 100), "count": st.session_state.get(f"rev_count_{i}", 0)} for i in range(st.session_state.get("revenue_selectors_count", 1))],
        "check_groups": st.session_state.get("check_groups", []),
        "input_blocks_count": st.session_state.get("input_blocks_count", 1)
    }
    save_today_draft(current_draft)

if "ball_selectors_count" not in st.session_state:
    st.session_state.ball_selectors_count = draft.get("ball_selectors_count", 1)
    st.session_state.revenue_selectors_count = draft.get("revenue_selectors_count", 1)
    st.session_state.input_blocks_count = draft.get("input_blocks_count", 1)
    st.session_state.check_groups = draft.get("check_groups", [])

tab_main, tab_check, tab_balls, tab_history = st.tabs(["📌 今日開團", "👥 收款名單", "👛 錢包", "📊 歷史"])

with tab_balls:
    st.header("👛 公積金錢包")
    col_w1, col_w2 = st.columns(2)
    with col_w1: st.metric("餘額", f"$ {int(st.session_state.wallet_balance)} 元")
    with col_w2:
        adjust = st.number_input("手動調整", value=0, step=100)
        if st.button("更新餘額"):
            st.session_state.wallet_balance += adjust
            save_config(st.session_state.wallet_balance, st.session_state.ball_types)
            st.rerun()

with tab_check:
    st.header("👥 現場收款")
    for b_idx in range(st.session_state.input_blocks_count):
        col_in1, col_in2 = st.columns([1, 2])
        price = col_in1.number_input("費率", value=250, step=10, key=f"in_price_{b_idx}")
        txt = col_in2.text_area("名單", key=f"in_txt_{b_idx}")
        if txt.strip() and st.button(f"加入群組 {b_idx+1}"):
            for line in txt.split("\n"):
                if line.strip(): st.session_state.check_groups.append({"raw": line.strip(), "price": price, "checked": False})
            sync_state_to_draft()
            st.rerun()
            
    for p_idx, player in enumerate(st.session_state.check_groups):
        # 這裡應用了您的版面要求
        col_ck1, col_ck2, col_ck3, col_ck4 = st.columns([0.5, 4.5, 1.5, 0.5])
        is_ck = col_ck1.checkbox("", value=player["checked"], key=f"ck_{p_idx}")
        col_ck2.write(f"~~{player['raw']}~~" if is_ck else player['raw'])
        col_ck3.write(f"${int(player['price'])}")
        if col_ck4.button("🗑️", key=f"del_{p_idx}"):
            st.session_state.check_groups.pop(p_idx)
            sync_state_to_draft()
            st.rerun()

with tab_main:
    st.header("🏢 場地費")
    c1_rate = st.number_input("場地1費用", value=int(draft.get("court_rate_1", 150)), step=50, key="c_rate_1", on_change=sync_state_to_draft)
    c1_hr = st.number_input("場地1小時", value=int(draft.get("court_hours_1", 0)), step=1, key="c_hours_1", on_change=sync_state_to_draft)
    c2_rate = st.number_input("場地2費用", value=int(draft.get("court_rate_2", 250)), step=50, key="c_rate_2", on_change=sync_state_to_draft)
    c2_hr = st.number_input("場地2小時", value=int(draft.get("court_hours_2", 0)), step=1, key="c_hours_2", on_change=sync_state_to_draft)
    
    st.divider()
    if st.button("結算今日"):
        revenue = sum(p["price"] for p in st.session_state.check_groups if p["checked"])
        expense = (c1_rate * c1_hr) + (c2_rate * c2_hr)
        add_history_record(datetime.now().strftime("%Y-%m-%d"), revenue, expense, revenue - expense, "結算")
        st.session_state.wallet_balance += (revenue - expense)
        save_config(st.session_state.wallet_balance, st.session_state.ball_types)
        st.success("結算完成！")

with tab_history:
    st.dataframe(load_history(), use_container_width=True)
