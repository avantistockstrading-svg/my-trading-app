from flask import Flask, request
import requests
import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta
import time
import yfinance as yf
import feedparser
import os
import random
from streamlit_autorefresh import st_autorefresh

# ===== API Configuration (Direct) =====
API_KEY = "7yyokKoC"
CLIENT_CODE = "S470211"
PASSWORD = "1234"
TOTP_SECRET = "P5XCUTXRKXQNNATBO5JZYM6SPI"

app = Flask(__name__)

# ===== Telegram Alert =====
def send_telegram(msg):
    token = "8780889811:AAEGAY61WhqBv2t4r0uW1mzACFrsSSgfl1c"
    chat_id = "1983026913"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": msg}, timeout=15)
    except:
        pass

# ===== NIFTY50 Symbols =====
NIFTY50_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "ITC.NS", "AXISBANK.NS", "WIPRO.NS", "HCLTECH.NS", "SUNPHARMA.NS",
    "MARUTI.NS", "TITAN.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "POWERGRID.NS"
]

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
    "NIFTY": {"token": "99926000", "exch": "NSE", "symbol": "NIFTY"},
    "CRUDEOIL": {"token": "210000", "exch": "MCX", "symbol": "CRUDEOIL"},
    "NATURALGAS": {"token": "210001", "exch": "MCX", "symbol": "NATURALGAS"}
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
    lot_size = {"NIFTY": 65, "CRUDEOIL": 100, "NATURALGAS": 1250}.get(market, 1)
    num_lots = st.number_input("📊 Lots", min_value=1, value=1)
    
    st.markdown(f"**Quantity:** {num_lots * lot_size}")
    st.markdown(f"**Today's Trades:** {st.session_state.nifty_trades_today if market=='NIFTY' else st.session_state.crude_trades_today if market=='CRUDEOIL' else st.session_state.ng_trades_today}/2")

# ===== Get Live Data =====
def get_market_intel(df):
    if df is None or df.empty:
        return {"Trend": "NEUTRAL", "Signal": "NONE", "SL": 0}
    
    c = df['close'].iloc[-1] if 'close' in df.columns else 0
    if 'ema9' not in df.columns or df['ema9'].isna().all():
        if len(df) >= 9 and 'close' in df.columns:
            df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    
    ema9 = df['ema9'].iloc[-1] if 'ema9' in df.columns else c
    trend = "BULLISH" if c > ema9 else "BEARISH"
    
    signal = "NONE"
    sl = 0
    
    if len(df) > 20 and 'ema20' in df.columns and 'rsi' in df.columns:
        try:
            ema20 = df['ema20'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            adx = df['adx'].iloc[-1] if 'adx' in df.columns else 25
            
            if c > ema20 and rsi < 70 and adx > 20:
                signal = "BUY"
                sl = round(c - 15)
            elif c < ema20 and rsi > 30 and adx > 20:
                signal = "SELL"
                sl = round(c + 15)
        except:
            pass
    
    return {"Trend": trend, "Signal": signal, "SL": sl}

# ===== Connect Angel One =====
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

# ===== Get Symbol =====
asset = SYMBOL_MAP[market]
symbol_map = {"NIFTY": "^NSEI", "CRUDEOIL": "CL=F", "NATURALGAS": "NG=F"}
df = yf.download(symbol_map[market], period="2d", interval="5m", progress=False, auto_adjust=False)

if not df.empty:
    df.columns = [str(c).lower() for c in df.columns]
    if 'adj close' in df.columns and 'close' not in df.columns:
        df.rename(columns={'adj close': 'close'}, inplace=True)
    
    df['ema9'] = ta.ema(df['close'], 9) if 'close' in df.columns else 0
    df['ema20'] = ta.ema(df['close'], 20) if 'close' in df.columns else 0
    df['rsi'] = ta.rsi(df['close'], 14) if 'close' in df.columns else 50
    if len(df) >= 20:
        adx_data = ta.adx(df['high'], df['low'], df['close'], length=14) if 'high' in df.columns else None
        df['adx'] = adx_data['ADX_14'] if adx_data is not None else 0

intel = get_market_intel(df)

# ===== Display =====
st.title("📈 RUDRANSH PRO-ALGO X")
st.markdown(f"### {market} Live Trading")

col1, col2, col3, col4 = st.columns(4)

if not df.empty and 'close' in df.columns:
    current_price = df['close'].iloc[-1]
    col1.metric("Current Price", f"₹{current_price:.2f}")
    
    signal_text = f"🔵 {intel['Signal']}" if intel['Signal'] == "BUY" else f"🔴 {intel['Signal']}" if intel['Signal'] == "SELL" else "⚪ WAIT"
    signal_color = "#00ff88" if intel['Signal'] == "BUY" else "#ff4b4b" if intel['Signal'] == "SELL" else "#facc15"
    col2.metric("Signal", signal_text)
    
    col3.metric("Trend", intel['Trend'])
    col4.metric("Stop Loss", f"₹{intel['SL']}" if intel['SL'] else "N/A")

# ===== Trading Logic with SL and Targets =====
now_time = datetime.now().time()
today = datetime.now().date()

if market == "NIFTY":
    start_time = datetime.now().replace(hour=9, minute=30).time()
    end_time = datetime.now().replace(hour=14, minute=30).time()
    max_trades = 2
    current_trades = st.session_state.nifty_trades_today
elif market == "CRUDEOIL":
    start_time = datetime.now().replace(hour=18, minute=0).time()
    end_time = datetime.now().replace(hour=22, minute=30).time()
    max_trades = 2
    current_trades = st.session_state.crude_trades_today
else:
    start_time = datetime.now().replace(hour=18, minute=0).time()
    end_time = datetime.now().replace(hour=22, minute=30).time()
    max_trades = 2
    current_trades = st.session_state.ng_trades_today

time_allowed = start_time <= now_time <= end_time
trade_limit_reached = current_trades >= max_trades
cooldown_ok = (datetime.now() - st.session_state.last_trade_time).seconds > 300

# Execute Trade
if st.session_state.algo_running and time_allowed and not trade_limit_reached and cooldown_ok and api:
    if intel['Signal'] == "BUY" and st.session_state.last_trade_side != "BUY":
        try:
            quantity = num_lots * lot_size
            api.placeOrder({
                "variety": "NORMAL",
                "tradingsymbol": asset['symbol'],
                "symboltoken": asset['token'],
                "transactiontype": "BUY",
                "exchange": asset['exch'],
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "quantity": str(quantity)
            })
            st.success(f"🚀 BUY {quantity} qty")
            send_telegram(f"🚀 BUY {market} | Qty: {quantity}")
            
            if market == "NIFTY":
                st.session_state.nifty_trades_today += 1
            elif market == "CRUDEOIL":
                st.session_state.crude_trades_today += 1
            else:
                st.session_state.ng_trades_today += 1
            
            st.session_state.last_trade_side = "BUY"
            st.session_state.last_trade_time = datetime.now()
            
        except Exception as e:
            st.error(f"BUY Error: {e}")
    
    elif intel['Signal'] == "SELL" and st.session_state.last_trade_side != "SELL":
        try:
            quantity = num_lots * lot_size
            api.placeOrder({
                "variety": "NORMAL",
                "tradingsymbol": asset['symbol'],
                "symboltoken": asset['token'],
                "transactiontype": "SELL",
                "exchange": asset['exch'],
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "quantity": str(quantity)
            })
            st.success(f"🔻 SELL {quantity} qty")
            send_telegram(f"🔻 SELL {market} | Qty: {quantity}")
            
            if market == "NIFTY":
                st.session_state.nifty_trades_today += 1
            elif market == "CRUDEOIL":
                st.session_state.crude_trades_today += 1
            else:
                st.session_state.ng_trades_today += 1
            
            st.session_state.last_trade_side = "SELL"
            st.session_state.last_trade_time = datetime.now()
            
        except Exception as e:
            st.error(f"SELL Error: {e}")

# ===== Status =====
if st.session_state.algo_running and time_allowed:
    st.success("🟢 ALGO IS RUNNING")
elif not time_allowed:
    st.info("⏰ Market closed. Algo will run during trading hours.")
else:
    st.warning("🔴 ALGO IS STOPPED")

st.caption("🔄 Auto Refresh Every 10 Seconds")
st_autorefresh(interval=10000, key="refresh")

st.markdown("---")
st.markdown("### 📊 Daily Trade Status")
col_d1, col_d2, col_d3 = st.columns(3)
col_d1.metric("NIFTY Trades", f"{st.session_state.nifty_trades_today}/2")
col_d2.metric("CRUDE Trades", f"{st.session_state.crude_trades_today}/2")
col_d3.metric("NG Trades", f"{st.session_state.ng_trades_today}/2")
