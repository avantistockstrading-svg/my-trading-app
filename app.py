import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import requests

# Telegram Alerts
def send_telegram(msg):
    token = "8780889811:AAEGAY61WhqBv2t4r0uW1mzACFrsSSgfl1c"
    chat_id = "1983026913"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=15)
    except Exception as e:
        print(f"Telegram error: {e}")

st.set_page_config(page_title="My Trading App", layout="wide")

st.title("📈 MY TRADING APP")
st.markdown("### Live Market Dashboard")

# Sidebar
with st.sidebar:
    st.markdown("## 🚀 CONTROL PANEL")
    
    if st.button("▶️ START ALGO"):
        st.success("Algo Started!")
        send_telegram("🚀 ALGO STARTED by user")
    
    if st.button("🛑 STOP ALGO"):
        st.warning("Algo Stopped!")
        send_telegram("🛑 ALGO STOPPED by user")

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
    
    # Signal Logic
    if change > 0.3:
        st.success("🔵 BUY SIGNAL DETECTED!")
        send_telegram(f"🔵 BUY SIGNAL | NIFTY at ₹{current:,.2f}")
    elif change < -0.3:
        st.error("🔴 SELL SIGNAL DETECTED!")
        send_telegram(f"🔴 SELL SIGNAL | NIFTY at ₹{current:,.2f}")
else:
    st.error("Unable to fetch market data")

st.success("✅ App is running successfully!")
