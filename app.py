import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
import time

# Telegram Alerts
def send_telegram(msg):
    token = "8780889811:AAEGAY61WhqBv2t4r0uW1mzACFrsSSgfl1c"
    chat_id = "1983026913"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=15)
        print(f"Telegram sent: {msg[:50]}... Response: {response.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

st.set_page_config(page_title="Rudransh Pro-Algo", layout="wide")

st.title("📈 RUDRANSH PRO-ALGO")
st.markdown("### Advanced Trading Signals")

# Sidebar
with st.sidebar:
    st.markdown("## 🚀 CONTROL")
    if st.button("▶️ START ALGO"):
        st.success("Started!")
        send_telegram("🚀 ALGO STARTED")
    if st.button("🛑 STOP ALGO"):
        st.warning("Stopped!")
        send_telegram("🛑 ALGO STOPPED")

# Get NIFTY data
nifty = yf.Ticker("^NSEI")
hist = nifty.history(period="7d")

if not hist.empty:
    current = hist['Close'].iloc[-1]
    prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
    change = ((current - prev) / prev) * 100
    
    # Calculate EMA
    if len(hist) >= 20:
        hist['EMA9'] = hist['Close'].ewm(span=9, adjust=False).mean()
        hist['EMA20'] = hist['Close'].ewm(span=20, adjust=False).mean()
        
        ema9 = hist['EMA9'].iloc[-1]
        ema20 = hist['EMA20'].iloc[-1]
        prev_ema9 = hist['EMA9'].iloc[-2]
        prev_ema20 = hist['EMA20'].iloc[-2]
        
        # Signal Logic
        if prev_ema9 <= prev_ema20 and ema9 > ema20 and change > 0:
            signal = "🔵 BUY"
            st.balloons()
            send_telegram(f"🔵 BUY SIGNAL | NIFTY {current:.2f}")
        elif prev_ema9 >= prev_ema20 and ema9 < ema20 and change < 0:
            signal = "🔴 SELL"
            send_telegram(f"🔴 SELL SIGNAL | NIFTY {current:.2f}")
        else:
            signal = "🟡 WAIT"
    else:
        if change > 0.2:
            signal = "🔵 BUY"
            send_telegram(f"🔵 BUY SIGNAL | NIFTY {current:.2f}")
        elif change < -0.2:
            signal = "🔴 SELL"
            send_telegram(f"🔴 SELL SIGNAL | NIFTY {current:.2f}")
        else:
            signal = "🟡 WAIT"
    
    # Display
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🇮🇳 NIFTY", f"₹{current:,.2f}", f"{change:+.2f}%")
    col2.metric("SIGNAL", signal)
    col3.metric("SUPPORT", f"₹{current-100:,.0f}")
    col4.metric("RESISTANCE", f"₹{current+100:,.0f}")
    
    st.info(f"🟢 ALGO RUNNING | {datetime.now().strftime('%H:%M:%S')}")
    st.caption("🔄 Auto refreshes every 10 seconds")
    
    # Auto refresh with rerun
    time.sleep(10)
    st.rerun()

else:
    st.error("No data")

st.success("✅ App Running")
