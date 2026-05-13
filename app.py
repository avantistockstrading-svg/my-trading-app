import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pyotp
import yfinance as yf
import requests
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# ===== Telegram Alerts =====
def send_telegram(msg):
    token = "8780889811:AAEGAY61WhqBv2t4r0uW1mzACFrsSSgfl1c"
    chat_id = "1983026913"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=15)
    except:
        pass

# ===== API Configuration =====
API_KEY = "7yyokKoC"
CLIENT_CODE = "S470211"
PASSWORD = "1234"
TOTP_SECRET = "P5XCUTXRKXQNNATBO5JZYM6SPI"

# ===== Symbol Mapping =====
SYMBOL_MAP = {
    "NIFTY": {"token": "99926000", "exch": "NSE", "symbol": "NIFTY"},
    "CRUDEOIL": {"token": "210000", "exch": "MCX", "symbol": "CRUDEOIL"},
    "NATURALGAS": {"token": "210001", "exch": "MCX", "symbol": "NATURALGAS"}
}

# ===== Session State =====
if "algo_running" not in st.session_state:
    st.session_state.algo_running = False
if "last_trade_time" not in st.session_state:
    st.session_state.last_trade_time = datetime.now() - timedelta(minutes=10)
if "nifty_trades_today" not in st.session_state:
    st.session_state.nifty_trades_today = 0
if "crude_trades_today" not in st.session_state:
    st.session_state.crude_trades_today = 0
if "ng_trades_today" not in st.session_state:
    st.session_state.ng_trades_today = 0
if "last_trade_date" not in st.session_state:
    st.session_state.last_trade_date = datetime.now().date()

# Reset daily counters
if datetime.now().date() != st.session_state.last_trade_date:
    st.session_state.nifty_trades_today = 0
    st.session_state.crude_trades_today = 0
    st.session_state.ng_trades_today = 0
    st.session_state.last_trade_date = datetime.now().date()

# ===== Page Config =====
st.set_page_config(page_title="RUDRANSH PRO-ALGO X", layout="wide")

# ===== Custom CSS =====
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #050816 0%, #0b1120 45%, #020617 100%);
    color: white;
}
[data-testid="metric-container"] {
    background: linear-gradient(145deg, rgba(15,23,42,0.95), rgba(30,41,59,0.88));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 22px;
}
.stButton > button {
    background: linear-gradient(135deg, #ff004f, #00ff88);
    border-radius: 16px;
    font-weight: bold;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ===== Title =====
st.markdown("<h1 style='text-align:center;'>📈 RUDRANSH PRO-ALGO X</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Advanced Multi-Asset Trading Algorithm</p>", unsafe_allow_html=True)

# ===== Sidebar =====
with st.sidebar:
    st.markdown("## 🚀 CONTROL PANEL")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ START"):
            st.session_state.algo_running = True
            send_telegram("🤖 ALGO STARTED")
            st.success("Started!")
    with col2:
        if st.button("🛑 STOP"):
            st.session_state.algo_running = False
            send_telegram("🛑 ALGO STOPPED")
            st.warning("Stopped!")
    
    st.markdown("---")
    
    market = st.selectbox("📌 Select Asset", list(SYMBOL_MAP.keys()))
    lot_size = {"NIFTY": 65, "CRUDEOIL": 100, "NATURALGAS": 1250}.get(market, 1)
    num_lots = st.number_input("📊 Number of Lots", min_value=1, value=1)
    
    st.markdown(f"""
    <div style='background:#1e293b; padding:15px; border-radius:12px; text-align:center;'>
        <span style='color:#9ca3af;'>Total Quantity</span><br>
        <span style='color:#00ff88; font-size:24px;'>{num_lots * lot_size}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(f"**Daily Trades:** NIFTY: {st.session_state.nifty_trades_today}/2 | CRUDE: {st.session_state.crude_trades_today}/2 | NG: {st.session_state.ng_trades_today}/2")

# ===== Connect to Angel One =====
def get_api():
    try:
        api = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = api.generateSession(CLIENT_CODE, PASSWORD, totp)
        if data['status']:
            st.success("✅ Angel One Connected")
            return api
    except Exception as e:
        st.error(f"API Error: {e}")
    return None

api = get_api()

# ===== Get Live Data =====
def get_live_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="5m")
        if not hist.empty:
            return hist
    except:
        pass
    return None

# ===== Trading Logic =====
trading_hours = False
now = datetime.now()
if market == "NIFTY":
    trading_hours = 9 <= now.hour <= 15
elif market in ["CRUDEOIL", "NATURALGAS"]:
    trading_hours = 9 <= now.hour <= 23

if trading_hours and st.session_state.algo_running:
    symbol_map = {"NIFTY": "^NSEI", "CRUDEOIL": "CL=F", "NATURALGAS": "NG=F"}
    df = get_live_data(symbol_map[market])
    
    if df is not None and not df.empty:
        df['EMA9'] = ta.ema(df['Close'], 9)
        df['EMA20'] = ta.ema(df['Close'], 20)
        df['RSI'] = ta.rsi(df['Close'], 14)
        
        current = df['Close'].iloc[-1]
        ema9 = df['EMA9'].iloc[-1]
        ema20 = df['EMA20'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        
        # Buy Condition
        buy_condition = (ema9 > ema20 and rsi < 70 and current > df['Open'].iloc[-1])
        # Sell Condition
        sell_condition = (ema9 < ema20 and rsi > 30 and current < df['Open'].iloc[-1])
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"₹{current:.2f}")
        
        if buy_condition:
            col2.metric("Signal", "🔵 BUY", delta="Strong")
            send_telegram(f"🔵 BUY {market} at ₹{current:.2f}")
            st.balloons()
        elif sell_condition:
            col2.metric("Signal", "🔴 SELL", delta="Strong")
            send_telegram(f"🔴 SELL {market} at ₹{current:.2f}")
        else:
            col2.metric("Signal", "🟡 WAIT", delta="No Signal")
        
        col3.metric("EMA 9", f"₹{ema9:.2f}")
        col4.metric("RSI", f"{rsi:.1f}")
        
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=market, line=dict(color='#00ff88', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA9'], mode='lines', name='EMA 9', line=dict(color='#ff004f', width=1)))
        fig.update_layout(template="plotly_dark", height=400, title=f"{market} Live Chart")
        st.plotly_chart(fig, use_container_width=True)
        
    else:
        st.warning("Waiting for data...")
else:
    if not trading_hours:
        st.info("⏰ Market closed. Algo will run during trading hours.")
    if not st.session_state.algo_running:
        st.info("🟡 Algo is stopped. Press START to begin.")

# ===== Real-time Status =====
if st.session_state.algo_running and trading_hours:
    st.success("🟢 ALGO IS RUNNING")
else:
    st.warning("🔴 ALGO IS STOPPED")

st.caption("🔄 Auto Refresh Every 10 Seconds")
st_autorefresh(interval=10000, key="auto_refresh")

st.markdown("---")
st.markdown("<p style='text-align:center;'>🚀 RUDRANSH PRO-ALGO X | Multi-Asset Trading Algorithm</p>", unsafe_allow_html=True)
