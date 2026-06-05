import streamlit as st
import random
from openai import OpenAI

st.set_page_config(page_title="玄機看盤", layout="wide")

# 更徹底移除頂部空白
st.markdown("""
<style>
    header {visibility: hidden;}
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem;
        margin-top: -1.5rem !important;
    }
    .stButton button {
        width: 100%;
        border-radius: 12px;
    }
    /* 自訂卡片與刪除按鈕融合樣式 */
    .card-delete-row {
        display: flex;
        align-items: stretch;
        gap: 0px;
        margin-bottom: 8px;
    }
    .card-button {
        flex: 5;
    }
    .delete-button {
        flex: 1;
        margin-left: -2px;
    }
    .delete-button button {
        background-color: #262730;
        border-left: none;
        border-radius: 0 12px 12px 0;
    }
    .card-button button {
        border-radius: 12px 0 0 12px;
        text-align: left;
        background-color: #262730;
        border-right: none;
    }
    /* 調整按鈕文字樣式 */
    .stButton button p {
        margin: 0;
    }
    .positive-arrow {
        color: #ff4b4b;
    }
    .negative-arrow {
        color: #0ecb81;
    }
</style>
""", unsafe_allow_html=True)

DEEPSEEK_API_KEY = ""  # 填入你的 Key

# ---------- 模擬數據 ----------
def get_stock_info(ticker):
    prev_close = 150.0 + random.uniform(-10, 10)
    change = random.uniform(-5, 5)
    price = prev_close + change
    pct = (change / prev_close) * 100 if prev_close != 0 else 0
    return price, change, pct

def get_tw_index():
    prev_close = 45000 + random.uniform(-500, 500)
    change = random.uniform(-200, 200)
    index = prev_close + change
    pct = (change / prev_close) * 100 if prev_close != 0 else 0
    vol = 3000000000 + random.uniform(-500000000, 500000000)
    return index, change, pct, vol

# ---------- 初始化 ----------
if "watchlist" not in st.session_state:
    st.session_state.watchlist = {
        "可成": "2474.TW",
        "嘉晶": "3016.TW",
        "精材": "3374.TW",
        "鴻海": "2317.TW",
        "台積電": "2330.TW",
        "南亞科": "2408.TW"
    }
if "selected" not in st.session_state:
    st.session_state.selected = "大盤"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------- 輔助 ----------
def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0

# ---------- 版面 ----------
col_left, col_mid, col_right = st.columns([1.2, 3, 1.2])

# ========== 左側：可點擊卡片 + 內嵌刪除 ==========
with col_left:
    st.markdown("### 📌 自選清單")
    items = list(st.session_state.watchlist.items())
    # 每行兩個股票
    for i in range(0, len(items), 2):
        row_cols = st.columns(2)
        for j in range(2):
            if i+j < len(items):
                name, ticker = items[i+j]
                price, change, pct = get_stock_info(ticker)
                # 漲跌符號與文字
                if change >= 0:
                    arrow = "📈"
                    sign = "+"
                else:
                    arrow = "📉"
                    sign = ""
                price_str = f"{price:.2f}"
                delta_str = f"{sign}{change:.2f} ({sign}{pct:.2f}%)"
                btn_label = f"{name}\n{price_str}\n{arrow} {delta_str}"
                
                with row_cols[j]:
                    # 使用兩欄：主卡片（點擊選股） + 刪除按鈕（小圖示）
                    col_card, col_del = st.columns([5, 1])
                    with col_card:
                        if st.button(btn_label, key=f"card_{name}", use_container_width=True):
                            st.session_state.selected = name
                            st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_{name}", use_container_width=True):
                            del st.session_state.watchlist[name]
                            if st.session_state.selected == name:
                                st.session_state.selected = "大盤"
                            st.rerun()
    st.caption("💡 點擊卡片查看個股，點🗑️刪除")

# ========== 中間欄（不變） ==========
with col_mid:
    st.markdown("#### 🔍 搜尋股票")
    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        search_ticker = st.text_input("", placeholder="例如 2317 或 2330.TW", label_visibility="collapsed")
    with col_search2:
        search_clicked = st.button("搜尋", use_container_width=True)
    
    if search_clicked and search_ticker:
        if search_ticker.isdigit():
            search_ticker = f"{search_ticker}.TW"
        price, change, pct = get_stock_info(search_ticker)
        if price:
            st.success(f"{search_ticker} 最新價 {price:.2f} ({change:+.2f})")
            if st.button("➕ 加入自選清單", key="add_from_search"):
                st.session_state.watchlist[search_ticker] = search_ticker
                st.rerun()
        else:
            st.error("查無此股票")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("🏠 大盤", use_container_width=True):
            st.session_state.selected = "大盤"
            st.rerun()
    with col_b2:
        if st.button("台股", use_container_width=True):
            st.session_state.selected = "台股模式"
    with col_b3:
        if st.button("美股", use_container_width=True):
            st.session_state.selected = "美股模式"
    
    st.markdown("---")
    
    if st.session_state.selected == "大盤":
        idx, chg, pct, vol = get_tw_index()
        delta_color = "inverse" if chg >= 0 else "normal"
        st.metric("加權指數", f"{idx:,.2f}", delta=f"{chg:+.2f} ({pct:+.2f}%)", delta_color=delta_color)
        st.caption(f"成交量 {vol:,.0f}")
        chart_data = [idx - chg*0.8, idx - chg*0.5, idx - chg*0.2, idx]
        st.line_chart(chart_data)
    elif st.session_state.selected in ["台股模式", "美股模式"]:
        st.info("功能開發中，請選擇大盤或左側自選股")
    else:
        name = st.session_state.selected
        ticker = st.session_state.watchlist.get(name)
        if ticker:
            price, change, pct = get_stock_info(ticker)
            delta_color = "inverse" if change >= 0 else "normal"
            st.metric(name, f"{price:.2f}", delta=f"{change:+.2f} ({pct:+.2f}%)", delta_color=delta_color)
            hist = [price - change*0.5, price - change*0.2, price]
            st.line_chart(hist)
        else:
            st.error("找不到該股票")

# ========== 右側對話（不變） ==========
with col_right:
    st.markdown("### 💬 玄機")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    user_input = st.chat_input("問問題…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        if DEEPSEEK_API_KEY:
            try:
                client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
                resp = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": user_input}],
                    temperature=0.3
                )
                ans = resp.choices[0].message.content
            except Exception as e:
                ans = f"AI 錯誤: {e}"
        else:
            ans = "請設定 DeepSeek API Key"
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()