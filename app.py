import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
import yfinance as yf
import requests
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# ===== Telegram Alert =====
def send_telegram(msg):
    token = "8780889811:AAEGAY61WhqBv2t4r0uW1mzACFrsSSgfl1c"
    chat_id = "1983026913"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=15)
    except:
        pass

# ===== Session State =====
if "nifty_trades_today" not in st.session_state:
    st.session_state.nifty_trades_today = 0
if "crude_trades_today" not in st.session_state:
    st.session_state.crude_trades_today = 0
if "ng_trades_today" not in st.session_state:
    st.session_state.ng_trades_today = 0
if "last_trade_date" not in st.session_state:
    st.session_state.last_trade_date = datetime.now().date()
if "algo_running" not in st.session_state:
    st.session_state.algo_running = False
if "last_trade_side" not in st.session_state:
    st.session_state.last_trade_side = ""
if "last_trade_time" not in st.session_state:
    st.session_state.last_trade_time = datetime.now() - timedelta(minutes=10)

# Reset daily
if datetime.now().date() != st.session_state.last_trade_date:
    st.session_state.nifty_trades_today = 0
    st.session_state.crude_trades_today = 0
    st.session_state.ng_trades_today = 0
    st.session_state.last_trade_date = datetime.now().date()

# ===== Page Config =====
st.set_page_config(page_title="RUDRANSH PRO-ALGO", layout="wide")

# ===== Symbol Mapping =====
SYMBOL_MAP = {
    "NIFTY": {"token": "99926000", "exch": "NSE", "symbol": "NIFTY", "yf": "^NSEI", "lot": 65},
    "CRUDEOIL": {"token": "210000", "exch": "MCX", "symbol": "CRUDEOIL", "yf": "CL=F", "lot": 100},
    "NATURALGAS": {"token": "210001", "exch": "MCX", "symbol": "NATURALGAS", "yf": "NG=F", "lot": 1250}
}

# ===== Sidebar =====
with st.sidebar:
    st.markdown("## 🚀 RUDRANSH PRO-ALGO")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ START", use_container_width=True):
            st.session_state.algo_running = True
            send_telegram("🤖 ALGO STARTED")
    with col2:
        if st.button("🛑 STOP", use_container_width=True):
            st.session_state.algo_running = False
            send_telegram("🛑 ALGO STOPPED")
    
    st.markdown("---")
    market = st.selectbox("📌 Select Asset", list(SYMBOL_MAP.keys()))
    asset = SYMBOL_MAP[market]
    num_lots = st.number_input("📊 Lots", min_value=1, value=1)
    quantity = num_lots * asset["lot"]
    
    st.markdown(f"**Quantity:** {quantity}")
    
    if market == "NIFTY":
        trades_today = st.session_state.nifty_trades_today
    elif market == "CRUDEOIL":
        trades_today = st.session_state.crude_trades_today
    else:
        trades_today = st.session_state.ng_trades_today
    
    st.markdown(f"**Today's Trades:** {trades_today}/2")

# ===== Get Market Data =====
def get_market_intel(df):
    if df is None or df.empty:
        return {"Trend": "NEUTRAL", "Signal": "NONE", "SL": 0}
    
    df.columns = [str(c).lower() for c in df.columns]
    if 'close' not in df.columns:
        return {"Trend": "NEUTRAL", "Signal": "NONE", "SL": 0}
    
    c = df['close'].iloc[-1]
    
    # Calculate indicators
    df['ema9'] = ta.ema(df['close'], 9)
    df['ema20'] = ta.ema(df['close'], 20)
    df['rsi'] = ta.rsi(df['close'], 14)
    
    ema9 = df['ema9'].iloc[-1] if not df['ema9'].isna().all() else c
    ema20 = df['ema20'].iloc[-1] if not df['ema20'].isna().all() else c
    rsi = df['rsi'].iloc[-1] if not df['rsi'].isna().all() else 50
    
    trend = "BULLISH 🚀" if c > ema9 else "BEARISH 🔻"
    
    # Signal Logic
    signal = "NONE"
    sl = 0
    
    if c > ema20 and rsi < 70:
        signal = "BUY"
        sl = round(c - 15, 2)
    elif c < ema20 and rsi > 30:
        signal = "SELL"
        sl = round(c + 15, 2)
    
    return {"Trend": trend, "Signal": signal, "SL": sl, "price": c, "ema9": ema9, "ema20": ema20, "rsi": rsi}

# Download data
df = yf.download(asset["yf"], period="2d", interval="5m", progress=False, auto_adjust=False)
intel = get_market_intel(df)

# ===== Display =====
st.title("📈 RUDRANSH PRO-ALGO X")
st.markdown(f"### {market} Live Trading")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Price", f"₹{intel['price']:.2f}")
col2.metric("Signal", f"🟢 {intel['Signal']}" if intel['Signal'] == "BUY" else f"🔴 {intel['Signal']}" if intel['Signal'] == "SELL" else "⚪ WAIT")
col3.metric("Trend", intel['Trend'])
col4.metric("Stop Loss", f"₹{intel['SL']}" if intel['SL'] else "N/A")

# Chart
if not df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=market, line=dict(color='#00ff88', width=2)))
    fig.update_layout(template="plotly_dark", height=400, title=f"{market} Price Chart")
    st.plotly_chart(fig, use_container_width=True)

# ===== Trading Logic =====
now = datetime.now()
if market == "NIFTY":
    start_time = now.replace(hour=9, minute=30).time()
    end_time = now.replace(hour=14, minute=30).time()
    max_trades = 2
else:
    start_time = now.replace(hour=18, minute=0).time()
    end_time = now.replace(hour=22, minute=30).time()
    max_trades = 2

time_allowed = start_time <= now.time() <= end_time
trade_limit_reached = trades_today >= max_trades
cooldown_ok = (datetime.now() - st.session_state.last_trade_time).seconds > 300

# Simulate Trading (without actual Angel One API)
if st.session_state.algo_running and time_allowed and not trade_limit_reached and cooldown_ok:
    if intel['Signal'] == "BUY" and st.session_state.last_trade_side != "BUY":
        st.success(f"🚀 BUY SIGNAL | {quantity} qty at ₹{intel['price']:.2f}")
        send_telegram(f"🚀 BUY {market} | Qty: {quantity} | Price: ₹{intel['price']:.2f}")
        
        if market == "NIFTY":
            st.session_state.nifty_trades_today += 1
        elif market == "CRUDEOIL":
            st.session_state.crude_trades_today += 1
        else:
            st.session_state.ng_trades_today += 1
        
        st.session_state.last_trade_side = "BUY"
        st.session_state.last_trade_time = datetime.now()
        st.balloons()
    
    elif intel['Signal'] == "SELL" and st.session_state.last_trade_side != "SELL":
        st.error(f"🔻 SELL SIGNAL | {quantity} qty at ₹{intel['price']:.2f}")
        send_telegram(f"🔻 SELL {market} | Qty: {quantity} | Price: ₹{intel['price']:.2f}")
        
        if market == "NIFTY":
            st.session_state.nifty_trades_today += 1
        elif market == "CRUDEOIL":
            st.session_state.crude_trades_today += 1
        else:
            st.session_state.ng_trades_today += 1
        
        st.session_state.last_trade_side = "SELL"
        st.session_state.last_trade_time = datetime.now()

# ===== Status =====
if st.session_state.algo_running and time_allowed:
    st.success("🟢 ALGO IS RUNNING")
elif not time_allowed:
    st.info("⏰ Market closed. Algo will run during trading hours.")
else:
    st.warning("🔴 ALGO IS STOPPED")

st.caption("🔄 Auto Refresh Every 10 Seconds")
st_autorefresh(interval=10000, key="refresh")

# ===== Daily Status =====
st.markdown("---")
st.markdown("### 📊 Daily Trade Status")
col_d1, col_d2, col_d3 = st.columns(3)
col_d1.metric("NIFTY Trades", f"{st.session_state.nifty_trades_today}/2")
col_d2.metric("CRUDE Trades", f"{st.session_state.crude_trades_today}/2")
col_d3.metric("NG Trades", f"{st.session_state.ng_trades_today}/2")
