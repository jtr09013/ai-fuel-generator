# ==========================================
# 盤後大盤指數 (加權改用 twstock，櫃買維持 yfinance)
# ==========================================
@st.cache_data(ttl=7200)  # 快取2小時，盤後資料不常變
def get_tw_index_after():
    data = {"taiex_p": 0.0, "taiex_c": 0.0, "taiex_pct": 0.0, "taiex_v": "待計算",
            "otc_p": 0.0, "otc_c": 0.0, "otc_pct": 0.0, "otc_v": "待確認"}

    # 1. 加權指數：使用 twstock 從證交所抓取歷史收盤 (無限制，穩定)
    try:
        # twstock.twse.daily_index() 回傳 list of dict，每個 dict 包含 date, open, high, low, close, change, change_percent
        idx_list = twstock.twse.daily_index()
        if idx_list and len(idx_list) >= 2:
            # 最近兩筆（最新為最後一筆）
            latest = idx_list[-1]
            prev = idx_list[-2]
            data["taiex_p"] = latest['close']
            data["taiex_c"] = latest['close'] - prev['close']
            data["taiex_pct"] = latest['change_percent']  # 直接使用內建的漲跌幅
            # 成交量不一定有，保留預設文字
        else:
            st.warning("twstock 加權指數資料不足")
    except Exception as e:
        st.warning(f"twstock 加權指數盤後抓取失敗: {e}，嘗試 yfinance 備援")
        # 備援：yfinance (萬一 twstock 失效)
        try:
            taiex = yf.Ticker("^TWII").history(period="5d")
            if len(taiex) >= 2:
                latest = taiex.iloc[-1]
                prev = taiex.iloc[-2]
                data["taiex_p"] = latest['Close']
                data["taiex_c"] = latest['Close'] - prev['Close']
                data["taiex_pct"] = (data["taiex_c"] / prev['Close']) * 100
                data["taiex_v"] = f"{latest['Volume']/1e6:.2f}百萬股"
        except Exception as e2:
            st.warning(f"yfinance 加權指數備援也失敗: {e2}")

    # 2. 櫃買指數 (維持 yfinance，目前穩定)
    try:
        otc = yf.Ticker("^TWOII").history(period="5d")
        if len(otc) >= 2:
            lo = otc.iloc[-1]
            po = otc.iloc[-2]
            data["otc_p"] = lo['Close']
            data["otc_c"] = lo['Close'] - po['Close']
            data["otc_pct"] = (data["otc_c"] / po['Close']) * 100
    except Exception as e:
        st.warning(f"櫃買指數盤後抓取失敗: {e}")

    return data
