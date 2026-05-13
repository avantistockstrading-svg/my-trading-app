import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="My Trading App", layout="wide")

st.title("📈 MY TRADING APP")
st.markdown("### Live Market Dashboard")

# Sidebar
with st.sidebar:
    st.markdown("## 🚀 CONTROL PANEL")
    if st.button("▶️ START ALGO"):
        st.success("Algo Started!")
    if st.button("🛑 STOP ALGO"):
        st.warning("Algo Stopped!")

# Get NIFTY data
nifty = yf.Ticker("^NSEI")
hist = nifty.history(period="1d")

if not hist.empty:
    current = hist['Close'].iloc[-1]
    change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100) if len(hist) > 1 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🇮🇳 NIFTY 50", f"₹{current:,.2f}", f"{change:+.2f}%")
    col2.metric("🎯 SIGNAL", "🟢 WAITING")
    col3.metric("🛡️ SUPPORT", f"₹{current-100:,.0f}")
    col4.metric("⚡ RESISTANCE", f"₹{current+100:,.0f}")
    
    st.info("🟢 ALGO IS READY | Waiting for market signals...")
    st.caption(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.error("Unable to fetch market data")

st.success("✅ App is running successfully!")
