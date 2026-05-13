import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import yfinance as yf
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import numpy as np

# Telegram Alert
def send_telegram(msg):
    token = "8780889811:AAEGAY61WhqBv2t4r0uW1mzACFrsSSgfl1c"
    chat_id = "1983026913"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=15)
    except:
        pass

# Session State
if "nifty_trades" not in st.session_state:
    st.session_state.nifty_trades = 0
if "crude_trades" not in st.session_state:
    st.session_state.crude_trades = 0
if "ng_trades" not in st.session_state:
    st.session_state.ng_trades = 0
if "algo_on" not in st.session_state:
    st.session_state.algo_on = False

st.set_page_config(page_title="Rudransh Pro-Algo", layout="wide")

# Sidebar
with st.sidebar:
    st.markdown("## 🚀 Controls")
    
    if st.button("▶️ START"):
        st.session_state.algo_on = True
        send_telegram("🤖 ALGO STARTED")
        st.success("Started!")
    
    if st.button("🛑 STOP"):
        st.session_state.algo_on = False
        send_telegram("🛑 ALGO STOPPED")
        st.warning("Stopped!")
    
    st.markdown("---")
    
    market = st.selectbox("Select Asset", ["NIFTY", "CRUDEOIL", "NATURALGAS"])
    
    if market == "NIFTY":
        symbol = "^NSEI"
        lot_size = 65
        trades = st.session_state.nifty_trades
    elif market == "CRUDEOIL":
        symbol = "CL=F"
        lot_size = 100
        trades = st.session_state.crude_trades
    else:
        symbol = "NG=F"
        lot_size = 1250
        trades = st.session_state.ng_trades
    
    lots = st.number_input("Lots", min_value=1, value=1, step=1)
    quantity = lots * lot_size
    
    st.metric("Quantity", quantity)
    st.metric("Today's Trades", f"{trades}/2")

# Get Data with fallback
try:
    df = yf.download(symbol, period="2d", interval="5m", progress=False)
    if df is None or df.empty or len(df) < 10:
        # Create safe demo data
        st.info("📡 Using demo data - Live data will appear during market hours")
        dates = pd.date_range(end=datetime.now(), periods=50, freq='5min')
        df = pd.DataFrame({
            'Open': 24500,
            'High': 24550,
            'Low': 24450,
            'Close': 24500,
            'Volume': 1000000
        }, index=dates)
        df['Close'] = df['Close'] + np.arange(len(df)) * 0.5
except Exception as e:
    st.info("📡 Demo mode - Waiting for market data")
    dates = pd.date_range(end=datetime.now(), periods=50, freq='5min')
    df = pd.DataFrame({
        'Open': 24500,
        'High': 24550,
        'Low': 24450,
        'Close': 24500,
        'Volume': 1000000
    }, index=dates)
    df['Close'] = df['Close'] + np.arange(len(df)) * 0.5

# Safe calculation with checks
df = df.copy()
close = df['Close'].dropna()

if len(close) > 0:
    current = float(close.iloc[-1])
    
    # Calculate indicators safely
    ema9_series = ta.ema(close, 9)
    ema20_series = ta.ema(close, 20)
    rsi_series = ta.rsi(close, 14)
    
    # Get latest values or use defaults
    ema9 = float(ema9_series.iloc[-1]) if len(ema9_series) > 0 and not pd.isna(ema9_series.iloc[-1]) else current
    ema20 = float(ema20_series.iloc[-1]) if len(ema20_series) > 0 and not pd.isna(ema20_series.iloc[-1]) else current
    rsi = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 and not pd.isna(rsi_series.iloc[-1]) else 50
else:
    current = 24500
    ema9 = 24500
    ema20 = 24500
    rsi = 50

# Signal Logic (safe)
signal = "WAIT"
sl = 0

try:
    if current > ema20 and rsi < 70:
        signal = "BUY"
        sl = current - 15
    elif current < ema20 and rsi > 30:
        signal = "SELL"
        sl = current + 15
except:
    signal = "WAIT"

# Market hours check
now = datetime.now()
market_hours = False

if market == "NIFTY":
    if 9 <= now.hour <= 15:
        market_hours = True
else:
    if 18 <= now.hour <= 23:
        market_hours = True

# Auto Trade
if st.session_state.algo_on and market_hours and trades < 2:
    if signal == "BUY":
        st.success(f"🚀 BUY SIGNAL at ₹{current:.2f}")
        send_telegram(f"🚀 BUY {market} | Qty: {quantity} | Price: ₹{current:.2f}")
        if market == "NIFTY":
            st.session_state.nifty_trades += 1
        elif market == "CRUDEOIL":
            st.session_state.crude_trades += 1
        else:
            st.session_state.ng_trades += 1
        st.balloons()
    elif signal == "SELL":
        st.error(f"🔻 SELL SIGNAL at ₹{current:.2f}")
        send_telegram(f"🔻 SELL {market} | Qty: {quantity} | Price: ₹{current:.2f}")
        if market == "NIFTY":
            st.session_state.nifty_trades += 1
        elif market == "CRUDEOIL":
            st.session_state.crude_trades += 1
        else:
            st.session_state.ng_trades += 1

# Display
st.title("📈 RUDRANSH PRO-ALGO")
st.markdown(f"### {market}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Price", f"₹{current:.2f}")
col2.metric("Signal", signal)
col3.metric("Trend", "BULLISH" if current > ema9 else "BEARISH")
col4.metric("Stop Loss", f"₹{sl:.2f}" if sl else "N/A")

col1, col2, col3 = st.columns(3)
col1.metric("EMA 9", f"₹{ema9:.2f}")
col2.metric("EMA 20", f"₹{ema20:.2f}")
col3.metric("RSI", f"{rsi:.1f}")

# Chart
try:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=market, line=dict(color='#00ff88', width=2)))
    fig.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig, use_container_width=True)
except:
    st.info("Chart loading...")

# Status
st.markdown("---")
if st.session_state.algo_on and market_hours:
    st.success("🟢 ALGO RUNNING")
elif not market_hours:
    st.info("⏰ Market closed. Algo will run during trading hours.")
else:
    st.warning("🔴 ALGO STOPPED")

st.caption("🔄 Auto refresh every 10 seconds")
st_autorefresh(interval=10000, key="refresh")

# Daily Trades
st.markdown("---")
st.markdown("### Daily Trades")
c1, c2, c3 = st.columns(3)
c1.metric("NIFTY", f"{st.session_state.nifty_trades}/2")
c2.metric("CRUDE", f"{st.session_state.crude_trades}/2")
c3.metric("NG", f"{st.session_state.ng_trades}/2")
