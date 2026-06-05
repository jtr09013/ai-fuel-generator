import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 必須先做這步設定
st.set_page_config(page_title="AI 數據燃料生產器", layout="wide")

# 2. 接著才開始寫標題
st.title("🚀 AI 財經數據燃料生產器")

# 3. 然後才是您的內容區塊
st.subheader("📊 市場情緒指標")
