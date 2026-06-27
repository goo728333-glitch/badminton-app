import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from datetime import datetime

st.set_page_config(page_title="阿杜羽球", page_icon="🏸", layout="centered")
st.title("🏸 阿杜羽球")

DB_DIR = os.path.expanduser("~/.badminton")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "badminton_pro.db")

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
    ball_types = json.loads(row[0]) if row else [{"name": "RSL No.4", "tube_price": 450, "count": 12}]
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

def load_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id as 編號, date as 日期, CAST(revenue AS INT) as 總收入, CAST(expense AS INT) as 總支出, CAST(profit AS INT) as 總利潤, note as 備註 FROM history ORDER BY id DESC", conn)
    conn.close()
    return df

def add_history_record(date, revenue, expense, profit, note):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (date, revenue, expense, profit, note) VALUES (?, ?, ?, ?, ?)", (date, int(revenue), int(expense), int(profit), note))
    conn.commit()
    conn.close()

init_db()
if "wallet_balance" not in st.session_state:
    st.session_state.wallet_balance, st.session_state.ball_types = load_config()

draft = load_today_draft() or {
    "c_rate_1": 0, "c_hours_1": 0, "c_rate_2": 0, "c_hours_2": 0,
    "check_groups": [], "input_blocks": 1
}

def sync():
    save_today_draft({
        "c_rate_1": st.session_state.get("c_rate_1", 0), "c_hours_1": st.session_state.get("c_hours_1", 0),
        "c_rate_2": st.session_state.get("c_rate_2", 0), "c_hours_2": st.session_state.get("c_hours_2", 0),
        "check_groups": st.session_state.check_groups, "input_blocks": st.session_state.input_blocks
    })

if "check_groups" not in st.session_state:
    st.session_state.check_groups = draft.get("check_groups", [])
    st.session_state.input_blocks = draft.get("input_blocks", 1)

tab1, tab2, tab3, tab4 = st.tabs(["📌 今日對帳", "👥 現場收款", "👛 錢包管理", "📊 歷史記錄"])

with tab2:
    st.header("👥 現場名單收款")
    for i in range(st.session_state.input_blocks):
        c1, c2 = st.columns([1, 2])
        price = c1.number_input(f"費率 #{i+1}", value=0, step=10, key=f"p_in_{i}")
        txt = c2.text_area(f"名單 #{i+1}", height=80, key=f"t_in_{i}")
        if st.button(f"加入名單 #{i+1}", key=f"add_{i}"):
            for name in txt.split('\n'):
                if name.strip(): st.session_state.check_groups.append({"raw": name, "price": price, "checked": False})
            sync(); st.rerun()
    
    st.write("---")
    for idx, p in enumerate(st.session_state.check_groups):
        # 關鍵排版：確保垃圾桶緊貼最右側
        cols = st.columns([0.5, 3, 2, 0.5], vertical_alignment="center")
        is_ck = cols[0].checkbox("", value=p["checked"], key=f"ck_{idx}")
        cols[1].write(f"~~{p['raw']}~~" if is_ck else f"**{p['raw']}**")
        cols[2].write(f"**${int(p['price'])}**")
        if cols[3].button("🗑️", key=f"del_{idx}"):
            st.session_state.check_groups.pop(idx); sync(); st.rerun()
        p["checked"] = is_ck

with tab1:
    st.header("🏢 場地計算")
    r1, h1 = st.columns(2)
    st.session_state.c_rate_1 = r1.number_input("場地1費用", value=int(draft.get("c_rate_1", 0)), step=50)
    st.session_state.c_hours_1 = h1.number_input("場地1小時", value=int(draft.get("c_hours_1", 0)), step=1)
    
    r2, h2 = st.columns(2)
    st.session_state.c_rate_2 = r2.number_input("場地2費用", value=int(draft.get("c_rate_2", 0)), step=50)
    st.session_state.c_hours_2 = h2.number_input("場地2小時", value=int(draft.get("c_hours_2", 0)), step=1)
    
    if st.button("💾 結算今日"):
        total_rev = sum(p["price"] for p in st.session_state.check_groups if p["checked"])
        total_exp = int(st.session_state.c_rate_1 * st.session_state.c_hours_1 + st.session_state.c_rate_2 * st.session_state.c_hours_2)
        add_history_record(datetime.now().strftime("%Y-%m-%d"), total_rev, total_exp, total_rev - total_exp, "今日結算")
        st.session_state.wallet_balance += (total_rev - total_exp)
        save_config(st.session_state.wallet_balance, st.session_state.ball_types)
        st.success("結算完成！")

with tab3:
    st.metric("當前餘額", f"${st.session_state.wallet_balance}")
    if st.button("🚨 重置所有預設值為0"):
        save_today_draft(None); st.rerun()

with tab4:
    st.dataframe(load_history(), use_container_width=True)
