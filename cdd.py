import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 網頁基本設定
st.set_page_config(page_title="AI 數據燃料生產器 v4.5", layout="wide")

# ==========================================
# 📊 核心數據抓取函式 (保持原本的高效台美分流邏輯)
# ==========================================
def get_stock_data(ticker, start_date, end_date):
    """通用抓取函數"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        if df.empty:
            return None
        df = df.reset_index()
        # 統一日期格式
        if 'Date' in df.columns:
            df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        elif 'Datetime' in df.columns:
            df['Datetime'] = df['Datetime'].dt.strftime('%Y-%m-%d %H:%M')
        return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
    except:
        return None

# ==========================================
# 🛠️ 主介面設計
# ==========================================
st.title("🚀 AI 財經數據燃料生產器 (動態清單版 v4.5)")
st.write("本系統已受 GitHub 帳號安全保護，僅供私人存取。")

# 側邊欄：日期設定
st.sidebar.header("📅 時間範圍設定")
start_date = st.sidebar.date_input("開始日期", datetime(2025, 1, 1))
end_date = st.sidebar.date_input("結束日期", datetime.today())

# 頁籤分流
tab1, tab2 = st.tabs(["🇹🇼 台股/大盤專區", "🇺🇸 美股專區"])

# --- 🇹🇼 台股專區 ---
with tab1:
    st.subheader("台灣股市動態數據抽取")
    
    # 🌟 方案 A 的動態個股管理箱
    tw_favorites = st.multiselect(
        "🔍 您的台股自訂觀察清單 (點擊框內可直接打字新增，點 X 可刪除)：",
        options=["2330", "2317", "2454", "0050", "0056"], # 這裡只放初始提示，您可以隨意增刪
        default=["2330", "2317"] # 預設勾選
    )
    
    # 手動輸入框 (作為備用或補充)
    tw_manual = st.text_input("✍️ 如果要臨時查詢清單外的台股，請輸入代號 (例如 2382)：", "")
    
    # 整合最終要抓取的台股清單
    tw_tickers = list(tw_favorites)
    if tw_manual.strip():
        tw_tickers.append(tw_manual.strip())
    
    if st.button("🔥 開始提煉台股數據燃料", key="tw_btn"):
        if not tw_tickers:
            st.warning("請先選擇或輸入至少一檔台股代號！")
        else:
            for tk in tw_tickers:
                formatted_tk = f"{tk}.TW"
                st.write(f"正在抽取 **{tk}** 的數據...")
                data = get_stock_data(formatted_tk, start_date, end_date)
                
                if data is not None:
                    st.success(f"🟢 {tk} 數據抽取成功！共 {len(data)} 筆紀錄")
                    st.dataframe(data.head(10), use_container_width=True)
                    
                    # 提供 CSV 下載按鈕
                    csv = data.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"💾 下載 {tk} 數據燃料包 (CSV)",
                        data=csv,
                        file_name=f"TW_{tk}_{datetime.today().strftime('%Y%m%d')}.csv",
                        mime='text/csv'
                    )
                else:
                    st.error(f"❌ 無法取得 {tk} 的數據，請檢查代號是否正確。")

# --- 🇺🇸 美股專區 ---
with tab2:
    st.subheader("美國股市動態數據抽取")
    
    # 🌟 方案 A 的動態個股管理箱 (美股)
    us_favorites = st.multiselect(
        "🔍 您的美股自訂觀察清單 (支援直接打字新增/刪除)：",
        options=["NVDA", "AAPL", "MSFT", "TSLA", "GOOG", "VOO"],
        default=["NVDA", "AAPL"]
    )
    
    us_manual = st.text_input("✍️ 如果要臨時查詢清單外的美股，請輸入代號 (例如 AMZN)：", "").upper()
    
    # 整合最終要抓取的美股清單
    us_tickers = list(us_favorites)
    if us_manual.strip():
        us_tickers.append(us_manual.strip())
        
    if st.button("🔥 開始提煉美股數據燃料", key="us_btn"):
        if not us_tickers:
            st.warning("請先選擇或輸入至少一檔美股代號！")
        else:
            for tk in us_tickers:
                st.write(f"正在抽取 **{tk}** 的數據...")
                data = get_stock_data(tk, start_date, end_date)
                
                if data is not None:
                    st.success(f"🟢 {tk} 數據抽取成功！共 {len(data)} 筆紀錄")
                    st.dataframe(data.head(10), use_container_width=True)
                    
                    # 提供 CSV 下載按鈕
                    csv = data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"💾 下載 {tk} 數據燃料包 (CSV)",
                        data=csv,
                        file_name=f"US_{tk}_{datetime.today().strftime('%Y%m%d')}.csv",
                        mime='text/csv'
                    )
                else:
                    st.error(f"❌ 無法取得 {tk} 的數據，請檢查代號是否正確。")
