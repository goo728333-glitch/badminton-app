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

# 在雲端環境中，將資料庫存在使用者目錄，確保重啟時資料不會被清空
DB_DIR = os.path.expanduser("~/.badminton")
os.makedirs(DB_DIR, exist_ok=True)
DB_FILE = os.path.join(DB_DIR, "badminton_pro.db")

# ==================== 永久資料庫 SQLite 核心連動 ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            revenue REAL,
            expense REAL,
            profit REAL,
            note TEXT
        )
    ''')
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
    if row:
        ball_types = json.loads(row[0])
    else:
        ball_types = [
            {"name": "RSL No.4", "tube_price": 450.0, "count": 12},
            {"name": "勝利比賽級", "tube_price": 540.0, "count": 12}
        ]
    conn.close()
    return wallet, ball_types

def save_config(wallet, ball_types):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    wallet_int = int(wallet)
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('wallet_balance', ?)", (str(wallet_int),))
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
    if row and row[0]:
        try:
            return json.loads(row[0])
        except:
            return None
    return None

def load_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id as 編號, date as 日期, CAST(revenue AS INT) as 總收入, CAST(expense AS INT) as 總支出, CAST(profit AS INT) as 總利潤, note as 備註 FROM history ORDER BY id DESC", conn)
    conn.close()
    return df

def add_history_record(date, revenue, expense, profit, note):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO history (date, revenue, expense, profit, note) VALUES (?, ?, ?, ?, ?)", 
                   (date, int(revenue), int(expense), int(profit), note))
    conn.commit()
    conn.close()

init_db()

if "wallet_balance" not in st.session_state or "ball_types" not in st.session_state:
    w_bal, b_types = load_config()
    st.session_state.wallet_balance = int(w_bal)
    st.session_state.ball_types = b_types

draft = load_today_draft()
if draft is None:
    draft = {
        "court_rate_1": 150, "court_hours_1": 0,
        "court_rate_2": 250, "court_hours_2": 0,
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
        "ball_selections": [
            {
                "name": st.session_state.get(f"sel_ball_{i}", ""),
                "count": st.session_state.get(f"sel_count_{i}", 0)
            } for i in range(st.session_state.get("ball_selectors_count", 1))
        ],
        "revenue_selectors_count": st.session_state.get("revenue_selectors_count", 1),
        "revenue_selections": [
            {
                "type": st.session_state.get(f"rev_type_{i}", "250"),
                "custom": st.session_state.get(f"rev_custom_{i}", 100),
                "count": st.session_state.get(f"rev_count_{i}", 0)
            } for i in range(st.session_state.get("revenue_selectors_count", 1))
        ],
        "check_groups": st.session_state.get("check_groups", []),
        "input_blocks_count": st.session_state.get("input_blocks_count", 1)
    }
    save_today_draft(current_draft)

if "court_rate_1" not in st.session_state:
    st.session_state.ball_selectors_count = draft.get("ball_selectors_count", 1)
    st.session_state.revenue_selectors_count = draft.get("revenue_selectors_count", 1)
    st.session_state.input_blocks_count = draft.get("input_blocks_count", 1)
    st.session_state.check_groups = draft.get("check_groups", [])

tab_main, tab_check, tab_balls, tab_history = st.tabs(["📌 今日開團對帳", "👥 現場名單收款", "👛 錢包與球種管理", "📊 歷史收支記帳本"])

with tab_balls:
    st.header("👛 公積金錢包")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        st.metric("當前錢包餘額", f"$ {int(st.session_state.wallet_balance)} 元")
    with col_w2:
        adjust_amount = st.number_input("管理員手動調整金額 (可正可負)", value=0, step=100)
        if st.button("💾 更新餘額"):
            st.session_state.wallet_balance = int(st.session_state.wallet_balance + adjust_amount)
            save_config(st.session_state.wallet_balance, st.session_state.ball_types)
            st.success("錢包餘額已儲存！")
            st.rerun()

    st.divider()
    st.subheader("💸 從錢包拿錢 (手動提領支出)")
    with st.expander("➕ 新增一筆錢包支出記錄"):
        expense_amount = st.number_input("支出金額 ($)", min_value=0, value=50, step=10)
        expense_note = st.text_input("支出原因/備註", placeholder="例如：買礦泉水")
        if st.button("🚨 確認從錢包扣款", type="primary"):
            if expense_amount > 0:
                st.session_state.wallet_balance = int(st.session_state.wallet_balance - expense_amount)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                add_history_record(now_str, 0, expense_amount, -expense_amount, f"【錢包提領】{expense_note}")
                save_config(st.session_state.wallet_balance, st.session_state.ball_types)
                st.success(f"已從錢包扣除 ${int(expense_amount)} 元！")
                st.rerun()

    st.divider()
    st.header("📦 球種與價格自訂")
    with st.expander("➕ 新增新球種/價格"):
        new_ball_name = st.text_input("球種名稱", placeholder="例如：YY AS-30")
        new_tube_price = st.number_input("一筒價格 ($)", min_value=0, value=500, step=10)
        new_ball_count = st.number_input("一筒有幾顆", min_value=1, value=12, step=1)
        if st.button("➕ 儲存新球種"):
            if new_ball_name:
                st.session_state.ball_types.append({
                    "name": new_ball_name, "tube_price": float(new_tube_price), "count": int(new_ball_count)
                })
                save_config(st.session_state.wallet_balance, st.session_state.ball_types)
                st.success(f"已儲存 {new_ball_name}")
                st.rerun()

    st.write("現有球箱：")
    for idx, b in enumerate(st.session_state.ball_types):
        per_price = b["tube_price"] / b["count"]
        c_b1, c_b2, c_b3 = st.columns([3, 3, 1])
        c_b1.write(f"**{b['name']}**")
        c_b2.write(f"一筒 ${int(b['tube_price'])} → 單顆: ${per_price:.0f}")
        if c_b3.button("🗑️", key=f"del_b_{idx}"):
            st.session_state.ball_types.pop(idx)
            save_config(st.session_state.wallet_balance, st.session_state.ball_types)
            st.rerun()

with tab_check:
    st.header("👥 現場球友收款確認")
    price_options = ["250", "240", "180", "170", "140", "💡 自行填寫金額"]
    st.write("### 📥 批量匯入名單區")
    
    current_inputs = []
    for b_idx in range(st.session_state.input_blocks_count):
        st.markdown(f"#### 💰 收費群組 #{b_idx+1}")
        col_in1, col_in2 = st.columns([2, 3])
        with col_in1:
            sel_price_type = st.selectbox("選擇此批名單費率", price_options, index=0, key=f"in_type_{b_idx}")
            if sel_price_type == "💡 自行填寫金額":
                final_p = st.number_input("輸入自訂金額", min_value=0, value=100, step=10, key=f"in_custom_{b_idx}")
            else:
                final_p = int(sel_price_type)
        with col_in2:
            txt_list = st.text_area("貼上名單", placeholder="1.小宗\n2.阿杜", height=100, key=f"in_txt_{b_idx}")
        current_inputs.append({"price": final_p, "text": txt_list})
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ 增加不同收費的名單區"):
            st.session_state.input_blocks_count += 1
            sync_state_to_draft()
            st.rerun()
    with col_btn2:
        if st.button("🚀 產生/重置全團收款對帳單", type="primary"):
            st.session_state.check_groups = []
            for block in current_inputs:
                if block["text"].strip():
                    lines = block["text"].split("\n")
                    for line in lines:
                        line = line.strip()
                        if not line: continue
                        st.session_state.check_groups.append({
                            "raw": line, "price": int(block["price"]), "checked": False
                        })
            sync_state_to_draft()
            st.success("🎉 全新收款對帳單已生成！")
            st.rerun()

    st.divider()
    if st.session_state.check_groups:
        st.write("### 📋 現場點名收款清單：")
        if st.button("🧹 清空當前所有球友名單"):
            st.session_state.check_groups = []
            sync_state_to_draft()
            st.success("已清空所有球友！")
            st.rerun()
            
        checked_count = sum(1 for p in st.session_state.check_groups if p["checked"])
        total_p_count = len(st.session_state.check_groups)
        st.progress(checked_count / total_p_count if total_p_count > 0 else 0)
        st.caption(f"目前收款進度： 已收 {checked_count} / {total_p_count} 人")
        
        need_rerun = False

        # 1. 注入 CSS，強制讓 class 為 right-buttons 的容器靠右對齊
        st.markdown("""
        <style>
        .right-buttons { display: flex; justify-content: flex-end; gap: 5px; }
        </style>
        """, unsafe_allow_html=True)

        for p_idx, player in enumerate(st.session_state.check_groups):
            # 建立三欄：[勾選] [姓名/金額] [右側按鈕區]
            c1, c2, c3 = st.columns([0.5, 4.0, 1.5])
            
            with c1:
                is_ck = st.checkbox("", value=player["checked"], key=f"ck_{p_idx}")
                st.session_state.check_groups[p_idx]["checked"] = is_ck
            
            with c2:
                # 姓名與金額並排
                display_text = f"~~{player['raw']}~~ - **${int(player['price'])}**" if is_ck else f"**{player['raw']}** - ${int(player['price'])}"
                st.write(display_text)
                
            with c3:
                # 使用 HTML div 包覆按鈕，強制靠右
                st.markdown('<div class="right-buttons">', unsafe_allow_html=True)
                
                # 編輯按鈕
                with st.popover("✏️"):
                    new_n = st.text_input("改名", value=player["raw"], key=f"n_{p_idx}")
                    new_p = st.number_input("改價", value=int(player["price"]), key=f"p_{p_idx}")
                    if st.button("確認", key=f"save_{p_idx}"):
                        st.session_state.check_groups[p_idx].update({"raw": new_n, "price": int(new_p)})
                        st.rerun()
                
                # 刪除按鈕
                if st.button("🗑️", key=f"del_{p_idx}"):
                    st.session_state.check_groups.pop(p_idx)
                    st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)
        # 這是您要修改的區塊結束
        if need_rerun: st.rerun()

with tab_main:
    st.header("🏢 2. 場地費計算")
    col_c1_rate, col_c1_hr = st.columns(2)
    with col_c1_rate:
        court_rate_1 = st.number_input("每小時費用 ($)", min_value=0, value=int(draft.get("court_rate_1", 150)), step=50, key="c_rate_1", on_change=sync_state_to_draft)
    with col_c1_hr:
        court_hours_1 = st.number_input("使用小時數", min_value=0, value=int(draft.get("court_hours_1", 0)), step=1, key="c_hours_1", on_change=sync_state_to_draft)
    subtotal_court_1 = court_rate_1 * court_hours_1

    col_c2_rate, col_c2_hr = st.columns(2)
    with col_c2_rate:
        court_rate_2 = st.number_input("每小時費用 ($) ", min_value=0, value=int(draft.get("court_rate_2", 250)), step=50, key="c_rate_2", on_change=sync_state_to_draft)
    with col_c2_hr:
        court_hours_2 = st.number_input("使用小時數 ", min_value=0, value=int(draft.get("court_hours_2", 0)), step=1, key="c_hours_2", on_change=sync_state_to_draft)
    subtotal_court_2 = court_rate_2 * court_hours_2
    
    total_court_fee = int(subtotal_court_1 + subtotal_court_2)
    st.caption(f"➔ 場地費總計 $ {total_court_fee} 元")

    st.divider()
    st.header("🏸 4. 消耗羽毛球計算")
    exact_ball_fee = 0.0
    used_balls_summary = []

    if not st.session_state.ball_types:
        st.warning("請先到『錢包與球種管理』分頁新增羽毛球資料！")
    else:
        ball_options = [b["name"] for b in st.session_state.ball_types]
        draft_ball_selections = draft.get("ball_selections", [])
        for f_idx in range(st.session_state.ball_selectors_count):
            col_sb1, col_sb2 = st.columns([2, 1])
            default_ball_name = ball_options[0]
            if f_idx < len(draft_ball_selections):
                saved_name = draft_ball_selections[f_idx].get("name", "")
                if saved_name in ball_options: default_ball_name = saved_name
            default_ball_count = 0
            if f_idx < len(draft_ball_selections): default_ball_count = int(draft_ball_selections[f_idx].get("count", 0))
                
            with col_sb1:
                selected_ball_name = st.selectbox(f"使用球種 #{f_idx+1}", ball_options, index=ball_options.index(default_ball_name), key=f"sel_ball_{f_idx}", on_change=sync_state_to_draft)
            with col_sb2:
                u_count = st.number_input("消耗顆數", min_value=0, value=default_ball_count, step=1, key=f"sel_count_{f_idx}", on_change=sync_state_to_draft)
            
            target_ball = next(b for b in st.session_state.ball_types if b["name"] == selected_ball_name)
            single_b_price = target_ball["tube_price"] / target_ball["count"]
            if u_count > 0:
                exact_ball_fee += single_b_price * u_count
                used_balls_summary.append(f"{selected_ball_name}*{u_count}顆")
        
        if st.button("➕ 增加使用其他球種"):
            st.session_state.ball_selectors_count += 1
            sync_state_to_draft()
            st.rerun()
        total_ball_fee = int(exact_ball_fee)
        st.caption(f"➔ 羽球成本總計 $ {total_ball_fee} 元")

    st.divider()
    st.header("💰 3. 現場收費總額計算")
    total_revenue = 0
    revenue_summary = []
    draft_rev_selections = draft.get("revenue_selections", [])
    
    for r_idx in range(st.session_state.revenue_selectors_count):
        st.write(f"**收費項目 #{r_idx+1}**")
        col_rev1, col_rev2, col_rev3 = st.columns([2, 2, 1])
        default_rev_type = "250"
        if r_idx < len(draft_rev_selections):
            saved_type = draft_rev_selections[r_idx].get("type", "250")
            if saved_type in price_options: default_rev_type = saved_type
        default_custom_p = 100
        if r_idx < len(draft_rev_selections): default_custom_p = int(draft_rev_selections[r_idx].get("custom", 100))
        default_rev_count = 0
        if r_idx < len(draft_rev_selections): default_rev_count = int(draft_rev_selections[r_idx].get("count", 0))
        
        with col_rev1:
            chosen_price_type = st.selectbox("選擇費率 / 類型", price_options, index=price_options.index(default_rev_type), key=f"rev_type_{r_idx}", on_change=sync_state_to_draft)
        
        final_unit_price = 0
        if chosen_price_type == "💡 自行填寫金額":
            with col_rev2:
                final_unit_price = st.number_input("請輸入自訂金額 ($)", min_value=0, value=default_custom_p, step=10, key=f"rev_custom_{r_idx}", on_change=sync_state_to_draft)
        else:
            final_unit_price = int(chosen_price_type)
            with col_rev2: st.write(f"單價：${final_unit_price} 元")
        with col_rev3:
            rev_p_count = st.number_input("人數 / 數量", min_value=0, value=default_rev_count, step=1, key=f"rev_count_{r_idx}", on_change=sync_state_to_draft)
            
        item_total = int(final_unit_price * rev_p_count)
        total_revenue += item_total
        if rev_p_count > 0: revenue_summary.append(f"{final_unit_price}*{rev_p_count}人")
            
    if st.button("➕ 增加開團其他收費項目"):
        st.session_state.revenue_selectors_count += 1
        sync_state_to_draft()
        st.rerun()
    st.caption(f"➔ 總收費小計 $ {total_revenue} 元")

    st.divider()
    total_expense = int(total_court_fee + total_ball_fee)
    net_profit = int(total_revenue - total_expense)
    
    st.subheader("📊 今日結算與錢包代墊設定")
    use_wallet_pay = st.checkbox("💡 代墊設定", value=False)
    
    m_c1, m_c2, m_c3 = st.columns(3)
    m_c1.metric("總收入", f"$ {total_revenue}")
    m_c2.metric("總成本", f"$ {total_expense}")
    m_c3.metric("淨利潤", f"$ {net_profit}")

    if st.button("💾 結算今日開團並連動錢包", type="primary"):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        balls_note = ", ".join(used_balls_summary) if used_balls_summary else "無用球"
        rev_note = ", ".join(revenue_summary) if revenue_summary else "無收入"
        court_note = f"{court_rate_1}*{court_hours_1}h"
        if court_hours_2 > 0: court_note += f" + {court_rate_2}*{court_hours_2}h"
        note_str = f"場地({court_note}), 球:{balls_note}, 收費({rev_note})" + (" (代墊)" if use_wallet_pay else "")
        
        add_history_record(now_str, total_revenue, total_expense, net_profit, note_str)
        st.session_state.wallet_balance = int(st.session_state.wallet_balance + net_profit)
        save_config(st.session_state.wallet_balance, st.session_state.ball_types)
        save_today_draft(None)
        
        st.session_state.ball_selectors_count = 1
        st.session_state.revenue_selectors_count = 1
        st.session_state.input_blocks_count = 1
        st.session_state.check_groups = []
        st.success("🎉 結算成功！")
        st.rerun()

with tab_history:
    st.header("📊 歷史記帳本 (永久儲存)")
    df_history = load_history()
    if df_history.empty: st.info("目前資料庫中還沒有任何歷史紀錄。")
    else: st.dataframe(df_history, use_container_width=True)
