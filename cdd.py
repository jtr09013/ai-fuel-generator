import os
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
os.environ["ANYIO_BACKEND"] = "asyncio"

# 富果行情 API
from fugle_marketdata import RestClient

from google import genai
from google.genai import types

from openai import OpenAI
from duckduckgo_search import DDGS
import requests

# ==========================================
# 頁面設定
# ==========================================
st.set_page_config(page_title="AI 數據燃料生產器 v5.0", layout="wide")
st.title("🚀 AI 財經數據燃料生產器")
st.caption("台股盤中：富果 API → Yahoo Finance 備援 | 美股：Yahoo Finance")

# ==========================================
# 上方大按鈕（取代 expander 摺疊）
# ==========================================
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "台股大包"

col_tab1, col_tab2, col_tab3 = st.columns(3)
with col_tab1:
    if st.button("🟢 台灣股市大包", use_container_width=True):
        st.session_state.active_tab = "台股大包"
with col_tab2:
    if st.button("🔵 美國股市大包", use_container_width=True):
        st.session_state.active_tab = "美股大包"
with col_tab3:
    if st.button("🔍 個股獨立單抓", use_container_width=True):
        st.session_state.active_tab = "個股單抓"

st.divider()

# ==========================================
# 台股即時報價函數（富果 + 備援）
# ==========================================
@st.cache_data(ttl=5)
def get_tw_stock_realtime(ticker):
    """台股即時報價：富果 -> yfinance -> 證交所（備援）"""
    ticker_clean = ticker.split('.')[0]
    ticker_yf = f"{ticker_clean}.TW"

    # 1. 富果 API
    try:
        api_key = st.secrets["FUGLE_API_KEY"]
        client = RestClient(api_key=api_key)
        quote = client.stock.intraday.quote(symbol=ticker_clean)
        if quote and quote.get('data'):
            d = quote['data']
            price = d.get('price')
            if price and price > 0:
                change = d.get('change', 0)
                pct = d.get('changePercent', 0)
                volume = d.get('volume', 0)
                prev_close = price - change
                vol_fmt = f"{volume/1000:.2f}萬張" if volume > 0 else "0張"
                return {"price": price, "prev_close": prev_close, "chg": change, "pct": pct, "vol": vol_fmt}
    except Exception as e:
        st.warning(f"富果 {ticker_clean} 失敗: {e}")

    # 2. yfinance 備援
    try:
        stock = yf.Ticker(ticker_yf)
        hist = stock.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            # 盤中最新價
            price = stock.fast_info.get('last_price', prev_close)
            if price > 0:
                volume = stock.fast_info.get('last_volume', 0)
                change = price - prev_close
                pct = (change / prev_close) * 100 if prev_close != 0 else 0
                vol_fmt = f"{volume/1000:.2f}萬張" if volume > 0 else "0張"
                return {"price": price, "prev_close": prev_close, "chg": change, "pct": pct, "vol": vol_fmt}
    except Exception as e:
        st.warning(f"yfinance {ticker_yf} 備援失敗: {e}")

    st.error(f"找不到股票 {ticker_clean}")
    return None

# ==========================================
# 大盤指數即時（使用 yfinance 加權指數 & 櫃買）
# ==========================================
@st.cache_data(ttl=10)
def get_tw_index_realtime():
    data = {
        "taiex_p": 0.0, "taiex_c": 0.0, "taiex_pct": 0.0, "taiex_v": "延遲",
        "otc_p": 0.0, "otc_c": 0.0, "otc_pct": 0.0, "otc_v": "延遲"
    }
    try:
        # 加權指數 ^TWII
        taiex = yf.Ticker("^TWII")
        hist = taiex.history(period="2d")
        if len(hist) >= 2:
            prev = hist['Close'].iloc[-2]
            # 抓當日1分鐘線最新價
            intra = taiex.history(period="1d", interval="1m")
            now = intra['Close'].iloc[-1] if not intra.empty else hist['Close'].iloc[-1]
            data["taiex_p"] = now
            data["taiex_c"] = now - prev
            data["taiex_pct"] = (data["taiex_c"] / prev) * 100
        # 櫃買指數 ^TWOII
        otc = yf.Ticker("^TWOII")
        hist_o = otc.history(period="2d")
        if len(hist_o) >= 2:
            prev_o = hist_o['Close'].iloc[-2]
            intra_o = otc.history(period="1d", interval="1m")
            now_o = intra_o['Close'].iloc[-1] if not intra_o.empty else hist_o['Close'].iloc[-1]
            data["otc_p"] = now_o
            data["otc_c"] = now_o - prev_o
            data["otc_pct"] = (data["otc_c"] / prev_o) * 100
    except Exception as e:
        st.warning(f"大盤抓取失敗: {e}")
    return data

# ==========================================
# 盤後模式（yfinance 日線）
# ==========================================
def get_tw_index_after():
    data = {"taiex_p": 0.0, "taiex_c": 0.0, "taiex_pct": 0.0, "taiex_v": "盤後",
            "otc_p": 0.0, "otc_c": 0.0, "otc_pct": 0.0, "otc_v": "盤後"}
    try:
        taiex = yf.Ticker("^TWII").history(period="5d")
        if len(taiex) >= 2:
            latest = taiex.iloc[-1]
            prev = taiex.iloc[-2]
            data["taiex_p"] = latest['Close']
            data["taiex_c"] = latest['Close'] - prev['Close']
            data["taiex_pct"] = (data["taiex_c"] / prev['Close']) * 100
            data["taiex_v"] = f"{latest['Volume']/1e6:.2f}百萬股"
        otc = yf.Ticker("^TWOII").history(period="5d")
        if len(otc) >= 2:
            lo = otc.iloc[-1]
            po = otc.iloc[-2]
            data["otc_p"] = lo['Close']
            data["otc_c"] = lo['Close'] - po['Close']
            data["otc_pct"] = (data["otc_c"] / po['Close']) * 100
    except:
        pass
    return data

def get_tw_stock_after(ticker):
    ticker_clean = ticker.split('.')[0]
    try:
        stock = yf.Ticker(f"{ticker_clean}.TW")
        hist = stock.history(period="5d")
        if len(hist) >= 2:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]
            price = latest['Close']
            prev_close = prev['Close']
            chg = price - prev_close
            pct = (chg / prev_close) * 100 if prev_close != 0 else 0
            vol = latest['Volume'] / 1000
            vol_str = f"{vol:.2f}萬張" if vol >= 10000 else f"{vol:.0f}張"
            return {"price": price, "prev_close": prev_close, "chg": chg, "pct": pct, "vol": vol_str}
    except:
        pass
    return None

# 美股、總經函數（保持原有，此處省略重複，請從你原始程式碼保留）
# 為了篇幅，這裡只列出必要框架，你需要把你原來的美股/總經函數複製回來
def get_us_index_data():
    indices = {"DOW": "^DJI", "NAS": "^IXIC", "SPX": "^GSPC", "SOX": "^SOX"}
    data = {}
    for name, ticker in indices.items():
        try:
            df = yf.Ticker(ticker).history(period="5d")
            if len(df) >= 2:
                latest = df.iloc[-1]
                prev = df.iloc[-2]
                chg = latest['Close'] - prev['Close']
                pct = (chg / prev['Close']) * 100
                data[name] = {"p": latest['Close'], "c": chg, "pct": pct}
            else:
                data[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
        except:
            data[name] = {"p": 0.0, "c": 0.0, "pct": 0.0}
    return data

def get_macro_raw():
    macro = {"WTI": 0.0, "WTI_CHG": 0.0, "US10Y": 0.0, "US10Y_CHG_BPS": 0.0, "DXY": 0.0, "DXY_CHG": 0.0}
    try:
        wti = yf.Ticker("CL=F").history(period="5d")
        if len(wti) >= 2:
            macro["WTI"] = wti['Close'].iloc[-1]
            macro["WTI_CHG"] = ((wti['Close'].iloc[-1] - wti['Close'].iloc[-2]) / wti['Close'].iloc[-2]) * 100
        tnx = yf.Ticker("^TNX").history(period="5d")
        if len(tnx) >= 2:
            macro["US10Y"] = tnx['Close'].iloc[-1]
            macro["US10Y_CHG_BPS"] = (tnx['Close'].iloc[-1] - tnx['Close'].iloc[-2]) * 100  
        dxy = yf.Ticker("DX-Y.NYB").history(period="5d")
        if dxy.empty:
            dxy = yf.Ticker("^DXY").history(period="5d")
        if len(dxy) >= 2:
            macro["DXY"] = dxy['Close'].iloc[-1]
            macro["DXY_CHG"] = ((dxy['Close'].iloc[-1] - dxy['Close'].iloc[-2]) / dxy['Close'].iloc[-2]) * 100
    except:
        pass
    return macro

def get_vix_data():
    try:
        vix = yf.Ticker("^VIX").history(period="5d")
        if len(vix) >= 2:
            return vix['Close'].iloc[-1], (vix['Close'].iloc[-1] - vix['Close'].iloc[-2])
    except:
        pass
    return 0.0, 0.0

def get_yahoo_news_titles(ticker, limit=1):
    try:
        stock = yf.Ticker(ticker)
        titles = [n.get('title', '').strip() for n in stock.news[:limit] if n.get('title')]
        return "、".join(titles) if titles else ""
    except:
        return ""

# ==========================================
# 動態顯示三個大頁面內容
# ==========================================
# ----- 頁面1：台股大包 -----
if st.session_state.active_tab == "台股大包":
    st.header("🇹🇼 台股大盤 + 關注個股")
    tw_time_mode = st.radio("時間狀態", ["☀️ 盤中即時", "🌙 盤後清算"], horizontal=True)
    tw_watchlist_input = st.text_input("輸入台股代號（逗號隔開）", value="2317, 3016, 3374")
    
    if st.button("🔥 產生台股數據包", type="primary"):
        with st.spinner("打包中..."):
            macro = get_macro_raw()
            watch_text = ""
            tickers = [t.strip() for t in tw_watchlist_input.split(",") if t.strip()]
            
            if "盤中即時" in tw_time_mode:
                idx = get_tw_index_realtime()
                for t in tickers:
                    res = get_tw_stock_realtime(t)
                    if res:
                        watch_text += f"{t}: {res['price']:.2f} ({res['chg']:+.2f} / {res['pct']:+.2f}%) 量:{res['vol']}\n"
                output = f"""
<TW_即時>
加權指數: {idx['taiex_p']:.2f} ({idx['taiex_c']:+.2f} / {idx['taiex_pct']:+.2f}%)
櫃買指數: {idx['otc_p']:.2f} ({idx['otc_c']:+.2f} / {idx['otc_pct']:+.2f}%)
關注股:\n{watch_text}
總經: DXY {macro['DXY']:.2f}  WTI {macro['WTI']:.2f}
</TW_即時>
"""
            else:
                idx = get_tw_index_after()
                for t in tickers:
                    res = get_tw_stock_after(t)
                    if res:
                        watch_text += f"{t}: 收{res['price']:.2f} ({res['chg']:+.2f} / {res['pct']:+.2f}%) 量:{res['vol']}\n"
                output = f"""
<TW_盤後>
加權指數收: {idx['taiex_p']:.2f} ({idx['taiex_c']:+.2f} / {idx['taiex_pct']:+.2f}%)
櫃買收: {idx['otc_p']:.2f} ({idx['otc_c']:+.2f} / {idx['otc_pct']:+.2f}%)
關注股:\n{watch_text}
</TW_盤後>
"""
            st.success("✅ 數據包已產生")
            st.code(output, language="text")

# ----- 頁面2：美股大包 -----
elif st.session_state.active_tab == "美股大包":
    st.header("🇺🇸 美股大盤 + 關注個股")
    us_time_mode = st.radio("時間狀態", ["☀️ 盤中即時", "🌙 盤後清算"], horizontal=True)
    us_watchlist = st.text_input("輸入美股代號（逗號隔開）", value="NVDA, MU, TSM")
    
    if st.button("🔥 產生美股數據包", type="primary"):
        with st.spinner("打包美股..."):
            idx = get_us_index_data()
            macro = get_macro_raw()
            vix_p, vix_c = get_vix_data()
            watch_text = ""
            for sym in [s.strip().upper() for s in us_watchlist.split(",") if s.strip()]:
                stock = yf.Ticker(sym)
                hist = stock.history(period="5d")
                if len(hist) >= 2:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    chg_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
                    vol = latest['Volume'] / 10000
                    vol_fmt = f"{vol:,.0f}萬股" if vol >= 1000 else f"{vol:.2f}萬股"
                    watch_text += f"{sym}: {latest['Close']:.2f} ({chg_pct:+.2f}%) 量:{vol_fmt}\n"
            output = f"""
<US_MARKET>
道瓊: {idx['DOW']['p']:.2f} ({idx['DOW']['c']:+.2f} / {idx['DOW']['pct']:+.2f}%)
那斯達克: {idx['NAS']['p']:.2f} ({idx['NAS']['pct']:+.2f}%)
標普: {idx['SPX']['p']:.2f} ({idx['SPX']['pct']:+.2f}%)
費半: {idx['SOX']['p']:.2f} ({idx['SOX']['pct']:+.2f}%)
VIX: {vix_p:.2f} ({vix_c:+.2f})
關注股:\n{watch_text}
總經: DXY {macro['DXY']:.2f}  油 {macro['WTI']:.2f}  10年债 {macro['US10Y']:.2f}%
</US_MARKET>
"""
            st.success("✅ 美股數據包")
            st.code(output, language="text")

# ----- 頁面3：個股單抓 -----
else:
    st.header("🔍 個股獨立資料包")
    market = st.radio("市場", ["台灣股市", "美國股市"], horizontal=True)
    single_code = st.text_input("輸入股票代號", value="3374").strip().upper()
    
    if st.button("⚡ 產生個股數據包", type="primary"):
        with st.spinner("抓取中..."):
            if market == "台灣股市":
                # 優先嘗試即時，失敗則盤後
                res = get_tw_stock_realtime(single_code)
                if not res:
                    res = get_tw_stock_after(single_code)
                if res:
                    news = get_yahoo_news_titles(f"{single_code}.TW", limit=2)
                    output = f"""
<單股分析>
股票: {single_code}
最新價: {res['price']:.2f}
漲跌: {res['chg']:+.2f} ({res['pct']:+.2f}%)
成交量: {res['vol']}
新聞: {news if news else '無'}
</單股分析>
"""
                    st.success(f"✅ {single_code} 資料")
                    st.code(output, language="text")
                else:
                    st.error("找不到該股票")
            else:
                # 美股
                stock = yf.Ticker(single_code)
                hist = stock.history(period="5d")
                if len(hist) >= 2:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    price = latest['Close']
                    prev_close = prev['Close']
                    chg = price - prev_close
                    pct = (chg / prev_close) * 100
                    vol_fmt = f"{latest['Volume']/10000:.2f}萬股"
                    news = get_yahoo_news_titles(single_code, limit=2)
                    output = f"""
<單股分析>
股票: {single_code}
最新價: {price:.2f}
漲跌: {chg:+.2f} ({pct:+.2f}%)
成交量: {vol_fmt}
新聞: {news if news else '無'}
</單股分析>
"""
                    st.success(f"✅ {single_code} 資料")
                    st.code(output, language="text")
                else:
                    st.error("找不到該股票")
