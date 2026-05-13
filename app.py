import streamlit as st
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from smartapi.smartConnect import SmartConnect  # ← हे बरोबर आहे
import pyotp
import yfinance as yf
import requests
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# ===== SECURITY - CHANGE THESE PASSWORDS =====
APP_PASSWORD = "Rudransh@8055"  # CHANGE THIS - App उघडताना विचारेल
TRADING_PIN = "1234"  # CHANGE THIS - Trade करण्यापूर्वी विचारेल
DAILY_LOSS_LIMIT = 100000  # ₹100000 loss झाला की auto stop

# ===== Angel One API Details =====
API_KEY = "7yyokKoC"
CLIENT_CODE = "S470211"
PASSWORD = "1234"
TOTP_SECRET = "P5XCUTXRKXQNNATBO5JZYM6SPI"

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
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "trading_auth" not in st.session_state:
    st.session_state.trading_auth = False
if "daily_loss" not in st.session_state:
    st.session_state.daily_loss = 0
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
    st.session_state.daily_loss = 0
    st.session_state.last_trade_date = datetime.now().date()

# ===== App Password Check =====
if not st.session_state.authenticated:
    st.set_page_config(page_title="RUDRANSH PRO-ALGO", layout="wide")
    st.title("🔐 SECURE ACCESS")
    password = st.text_input("Enter App Password", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong Password!")
    st.stop()

# ===== Page Config =====
st.set_page_config(page_title="RUDRANSH PRO-ALGO", layout="wide")

# ===== Symbol Mapping =====
SYMBOL_MAP = {
    "NIFTY": {"token": "99926000", "exch": "NSE", "symbol": "NIFTY", "yf": "^NSEI", "lot": 65},
    "CRUDEOIL": {"token": "210000", "exch": "MCX", "symbol": "CRUDEOIL", "yf": "CL=F", "lot": 100},
    "NATURALGAS": {"token": "210001", "exch": "MCX", "symbol": "NATURALGAS", "yf": "NG=F", "lot": 1250}
}

# ===== Connect to Angel One =====
def get_api():
    try:
        api = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = api.generateSession(CLIENT_CODE, PASSWORD, totp)
        if data['status']:
            return api
    except Exception as e:
        st.error(f"API Connection Error: {e}")
    return None

# ===== Get P&L =====
def get_current_pnl(api):
    try:
        pos = api.position()
        if pos and 'data' in pos:
            total_pnl = 0
            for p in pos['data']:
                total_pnl += float(p.get('pnl', 0))
            return total_pnl
    except:
        pass
    return 0

# ===== Execute Trade =====
def execute_trade(api, symbol, token, exchange, transaction_type, quantity, price):
    try:
        order = api.placeOrder({
            "variety": "NORMAL",
            "tradingsymbol": symbol,
            "symboltoken": token,
            "transactiontype": transaction_type,
            "exchange": exchange,
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "quantity": str(quantity)
        })
        return order
    except Exception as e:
        st.error(f"Trade Error: {e}")
        return None

# ===== Sidebar =====
with st.sidebar:
    st.markdown("## 🚀 RUDRANSH PRO-ALGO")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ START", use_container_width=True):
            if not st.session_state.trading_auth:
                st.warning("Enter Trading PIN first!")
            else:
                st.session_state.algo_running = True
                send_telegram("🤖 REAL ALGO STARTED - Live Trading Active")
    with col2:
        if st.button("🛑 STOP", use_container_width=True):
            st.session_state.algo_running = False
            send_telegram("🛑 ALGO STOPPED")
    
    st.markdown("---")
    
    # Trading PIN Authentication
    if not st.session_state.trading_auth:
        trading_pin = st.text_input("🔐 Trading PIN", type="password", placeholder="Enter PIN to trade")
        if st.button("Authorize Trading"):
            if trading_pin == TRADING_PIN:
                st.session_state.trading_auth = True
                st.success("Trading Authorized!")
                st.rerun()
            else:
                st.error("Wrong PIN!")
    
    if st.session_state.trading_auth:
        st.success("✅ Trading Authorized")
    
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
    st.markdown(f"**Today's P&L:** ₹{st.session_state.daily_loss:,.2f}")

# ===== Get Market Data =====
def get_market_intel(df):
    if df is None or df.empty:
        return {"Trend": "NEUTRAL", "Signal": "NONE", "SL": 0, "price": 0, "ema9": 0, "ema20": 0, "rsi": 50}
    
    df.columns = [str(c).lower() for c in df.columns]
    if 'close' not in df.columns:
        return {"Trend": "NEUTRAL", "Signal": "NONE", "SL": 0, "price": 0, "ema9": 0, "ema20": 0, "rsi": 50}
    
    c = df['close'].iloc[-1]
    df['ema9'] = ta.ema(df['close'], 9)
    df['ema20'] = ta.ema(df['close'], 20)
    df['rsi'] = ta.rsi(df['close'], 14)
    
    ema9 = df['ema9'].iloc[-1] if not df['ema9'].isna().all() else c
    ema20 = df['ema20'].iloc[-1] if not df['ema20'].isna().all() else c
    rsi = df['rsi'].iloc[-1] if not df['rsi'].isna().all() else 50
    
    trend = "BULLISH 🚀" if c > ema9 else "BEARISH 🔻"
    signal = "NONE"
    sl = 0
    
    if c > ema20 and rsi < 70:
        signal = "BUY"
        sl = round(c - 15, 2)
    elif c < ema20 and rsi > 30:
        signal = "SELL"
        sl = round(c + 15, 2)
    
    return {"Trend": trend, "Signal": signal, "SL": sl, "price": c, "ema9": ema9, "ema20": ema20, "rsi": rsi}

# ===== Fetch Data =====
try:
    df = yf.download(asset["yf"], period="2d", interval="5m", progress=False, auto_adjust=False, threads=False)
    if df is None or df.empty:
        raise Exception("No data")
except:
    st.info("📡 Waiting for market data...")
    dates = pd.date_range(end=datetime.now(), periods=50, freq='5min')
    base_price = 24500
    df = pd.DataFrame({
        'open': [base_price + i * 2 for i in range(50)],
        'high': [base_price + i * 2 + 10 for i in range(50)],
        'low': [base_price + i * 2 - 10 for i in range(50)],
        'close': [base_price + i * 2 + 5 for i in range(50)],
        'volume': [1000000] * 50
    }, index=dates)
    df.columns = ['open', 'high', 'low', 'close', 'volume']

intel = get_market_intel(df)

# ===== Display =====
st.title("📈 RUDRANSH PRO-ALGO X (REAL TRADING)")
st.markdown(f"### {market} Live Trading")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Price", f"₹{intel['price']:.2f}")
col2.metric("Signal", f"🟢 {intel['Signal']}" if intel['Signal'] == "BUY" else f"🔴 {intel['Signal']}" if intel['Signal'] == "SELL" else "⚪ WAIT")
col3.metric("Trend", intel['Trend'])
col4.metric("Stop Loss", f"₹{intel['SL']}" if intel['SL'] else "N/A")

st.markdown("---")
st.markdown("### 📊 Technical Indicators")
col_i1, col_i2, col_i3 = st.columns(3)
col_i1.metric("EMA 9", f"₹{intel['ema9']:.2f}")
col_i2.metric("EMA 20", f"₹{intel['ema20']:.2f}")
col_i3.metric("RSI", f"{intel['rsi']:.1f}")

# Chart
if not df.empty and 'close' in df.columns:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name=market, line=dict(color='#00ff88', width=2)))
    fig.update_layout(template="plotly_dark", height=400, title=f"{market} Price Chart")
    st.plotly_chart(fig, use_container_width=True)

# ===== Real Trading Logic =====
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
loss_limit_hit = st.session_state.daily_loss <= -DAILY_LOSS_LIMIT
cooldown_ok = (datetime.now() - st.session_state.last_trade_time).seconds > 300

# ===== Execute Real Trades =====
if (st.session_state.algo_running and st.session_state.trading_auth and 
    time_allowed and not trade_limit_reached and not loss_limit_hit and cooldown_ok):
    
    if intel['Signal'] == "BUY" and st.session_state.last_trade_side != "BUY":
        # Confirm trade
        confirm = st.checkbox(f"⚠️ Confirm BUY {quantity} qty {market} at ₹{intel['price']:.2f}?")
        if confirm:
            api = get_api()
            if api:
                result = execute_trade(api, asset['symbol'], asset['token'], asset['exch'], "BUY", quantity, intel['price'])
                if result:
                    st.success(f"🚀 LIVE BUY EXECUTED | {quantity} qty at ₹{intel['price']:.2f}")
                    send_telegram(f"🚀 LIVE BUY {market} | Qty: {quantity} | Price: ₹{intel['price']:.2f} | SL: ₹{intel['SL']}")
                    
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
        confirm = st.checkbox(f"⚠️ Confirm SELL {quantity} qty {market} at ₹{intel['price']:.2f}?")
        if confirm:
            api = get_api()
            if api:
                result = execute_trade(api, asset['symbol'], asset['token'], asset['exch'], "SELL", quantity, intel['price'])
                if result:
                    st.error(f"🔻 LIVE SELL EXECUTED | {quantity} qty at ₹{intel['price']:.2f}")
                    send_telegram(f"🔻 LIVE SELL {market} | Qty: {quantity} | Price: ₹{intel['price']:.2f} | SL: ₹{intel['SL']}")
                    
                    if market == "NIFTY":
                        st.session_state.nifty_trades_today += 1
                    elif market == "CRUDEOIL":
                        st.session_state.crude_trades_today += 1
                    else:
                        st.session_state.ng_trades_today += 1
                    
                    st.session_state.last_trade_side = "SELL"
                    st.session_state.last_trade_time = datetime.now()

# Update P&L
if st.session_state.trading_auth:
    api = get_api()
    if api:
        current_pnl = get_current_pnl(api)
        st.session_state.daily_loss = current_pnl

# ===== Status =====
st.markdown("---")
if loss_limit_hit:
    st.error(f"⚠️ DAILY LOSS LIMIT HIT (₹{DAILY_LOSS_LIMIT})! Trading Stopped.")
elif st.session_state.algo_running and time_allowed and st.session_state.trading_auth:
    st.success("🟢 REAL ALGO IS RUNNING - Live Trades Active")
elif not st.session_state.trading_auth:
    st.warning("🔐 Enter Trading PIN to enable live trades")
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

st.markdown("---")
st.markdown("<p style='text-align:center;'>🚀 RUDRANSH PRO-ALGO X | REAL TRADING ACTIVE</p>", unsafe_allow_html=True)
