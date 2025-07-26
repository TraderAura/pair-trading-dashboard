import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from io import StringIO
from datetime import datetime

# Set layout
st.set_page_config(layout="wide")
st.title("📊 Live Pair Trading Dashboard")

# --- Sidebar Configuration ---
stock1 = st.sidebar.selectbox("Select Stock 1", ["HDFCBANK.NS", "RELIANCE.NS", "ICICIBANK.NS"])
stock2 = st.sidebar.selectbox("Select Stock 2", ["INFY.NS", "TCS.NS", "WIPRO.NS"])
capital = st.sidebar.number_input("Capital per Pair (₹)", value=100000)
timeframe = st.sidebar.selectbox("Timeframe", ["1mo", "3mo", "6mo"])
interval = st.sidebar.selectbox("Candle Interval", ["15m", "30m", "1h", "1d"])
refresh = st.sidebar.button("🔄 Refresh Live Data")

# Initialize session state
if "ledger" not in st.session_state:
    st.session_state.ledger = []
if "positions" not in st.session_state:
    st.session_state.positions = {}

# Load Data
@st.cache_data(ttl=600)
def load_data(ticker1, ticker2, tf, interval):
    df1 = yf.download(ticker1, period=tf, interval=interval)["Close"]
    df2 = yf.download(ticker2, period=tf, interval=interval)["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [ticker1, ticker2]
    df = df.dropna()
    return df

data = load_data(stock1, stock2, timeframe, interval)

if data.empty or len(data) < 2:
    st.error("⚠️ Not enough data for this stock/timeframe combo. Try a longer timeframe or different stocks.")
    st.stop()


# Calculate spread and Z-score
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# --- Trade Signal Logic ---
z = data["Z-Score"].iloc[-1]
price1 = data[stock1].iloc[-1]
price2 = data[stock2].iloc[-1]
qty1 = qty2 = int(capital // ((price1 + price2) / 2))
signal = None

if z > 1.5:
    signal = f"Short {stock1}, Long {stock2}"
    st.session_state.positions[(stock1, stock2)] = ("short", price1, price2, qty1, qty2)
elif z < -1.5:
    signal = f"Long {stock1}, Short {stock2}"
    st.session_state.positions[(stock1, stock2)] = ("long", price1, price2, qty1, qty2)
elif -0.1 < z < 0.1 and (stock1, stock2) in st.session_state.positions:
    entry = st.session_state.positions.pop((stock1, stock2))
    direction, p1_in, p2_in, q1, q2 = entry

    # Calculate P&L
    if direction == "long":
        pnl = (price1 - p1_in) * q1 + (p2_in - price2) * q2
    else:
        pnl = (p2_in - price2) * q2 + (price1 - p1_in) * q1

    st.session_state.ledger.append({
        "timestamp": datetime.now().replace(tzinfo=None),
        "stock1": stock1,
        "stock2": stock2,
        "entry_type": direction,
        "exit_z": round(z, 2),
        "pnl": round(pnl, 2)
    })

# --- Display Chart ---
st.subheader("📈 Price & Spread")
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data[stock1], name=stock1))
fig.add_trace(go.Scatter(x=data.index, y=data[stock2], name=stock2))
fig.add_trace(go.Scatter(x=data.index, y=data["Spread"], name="Spread", yaxis="y2"))

fig.update_layout(
    yaxis=dict(title="Price"),
    yaxis2=dict(title="Spread", overlaying="y", side="right"),
    title="Stock Prices and Spread",
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig, use_container_width=True)

# --- Signal Display ---
if signal:
    st.success(f"📣 Trade Signal: {signal}")
else:
    st.info("📡 No active trade signal.")

# --- Ledger Display ---
ledger_df = pd.DataFrame(st.session_state.ledger)
if not ledger_df.empty:
    st.subheader("📒 Trade Ledger")
    st.dataframe(ledger_df, use_container_width=True)
    
    # P&L Summary
    st.metric("💸 Total P&L", f"₹ {ledger_df['pnl'].sum():,.2f}")

    # CSV Export
    csv_buffer = StringIO()
    ledger_df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 Download Ledger CSV",
        data=csv_buffer.getvalue(),
        file_name="pair_trading_ledger.csv",
        mime="text/csv"
    )
else:
    st.warning("🕰️ No closed trades yet.")

# --- Placeholder for Live NSE Data (to be added) ---
st.markdown("---")
st.markdown("⚠️ **Live NSE price integration coming next...**")

