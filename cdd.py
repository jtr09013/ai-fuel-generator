import streamlit as st
import yfinance as yf
import pandas as pd

# 設定頁面基礎配置
st.set_page_config(page_title="AI 財經數據燃料生產器", layout="wide")

st.title("🚀 AI 財經數據燃料生產器")

# 1. 動態自訂個股清單 (方案)
st.sidebar.header("⚙️ 設定觀察清單")
default_stocks = ["AAPL", "NVDA", "TSLA", "MSFT"]
user_stocks = st.sidebar.multiselect(
    "選擇您想追蹤的個股：",
    options=["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMD", "INTC", "META", "NFLX"],
    default=default_stocks
)

# 2. 顯示個股數據 (以 yfinance 抓取)
if user_stocks:
    st.subheader("📈 個股行情概覽")
    data = yf.download(user_stocks, period="1d")['Close']
    st.dataframe(data, use_container_width=True)
else:
    st.info("請在側邊欄選擇至少一支股票。")

# 3. 修正後的市場情緒指標 (VIX 與 PCR)
st.divider()
st.subheader("📊 市場情緒指標")

# 這裡假設數值來自您的數據源
vix_value = 18.86 
pcr_value = 1.07
prev_pcr = 0.452

# VIX 邏輯優化
vix_note = "恐慌情緒顯著升溫" if vix_value > 18 else "市場相對平穩"
st.write(f"**VIX:** {vix_value} | **NOTE:** {vix_note}")

# PCR 邏輯優化
st.write(f"**PUT/CALL RATIO:** {pcr_value} | **NOTE:** 較前日（{prev_pcr}）大幅上升，避險情緒顯著升溫")

st.success("數據更新完畢")