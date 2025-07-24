import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
from scipy import stats

# ---- Config ----
st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# ---- User Inputs ----
st.sidebar.header("🛠️ Trade Setup")
stock1 = st.sidebar.text_input("Stock 1 (e.g., BPCL.NS)", "BPCL.NS")
stock2 = st.sidebar.text_input("Stock 2 (e.g., IOC.NS)", "IOC.NS")
start = st.sidebar.date_input("Start Date", datetime(2024, 1, 1))
end = st.sidebar.date_input("End Date", datetime.today())
interval = st.sidebar.selectbox("Interval", ["1h", "1d", "15m"], index=0)
z_entry = st.sidebar.slider("Z-Score Entry Threshold", 1.0, 3.0, 1.5, 0.1)
z_exit = st.sidebar.slider("Z-Score Exit Threshold", -1.0, 1.0, 0.0, 0.1)
capital = st.sidebar.number_input("Initial Capital (₹)", value=100000)

# ---- Download Data ----
data1 = yf.download(stock1, start=start, end=end, interval=interval)
data2 = yf.download(stock2, start=start, end=end, interval=interval)
data = pd.DataFrame({stock1: data1['Adj Close'], stock2: data2['Adj Close']}).dropna()

# ---- Calculate Spread & Z-score ----
x = data[stock2]
y = data[stock1]
beta, alpha = np.polyfit(x, y, 1)
data['spread'] = y - (beta * x + alpha)
data['zscore'] = (data['spread'] - data['spread'].rolling(20).mean()) / data['spread'].rolling(20).std()

# ---- Strategy ----
position = 0
entry_price_spread = 0
entries = []

for i in range(len(data)):
    z = data['zscore'].iloc[i]
    dt = data.index[i]
    price1 = data[stock1].iloc[i]
    price2 = data[stock2].iloc[i]
    spread = data['spread'].iloc[i]

    if position == 0:
        if z > z_entry:
            position = -1  # Short stock1, Long stock2
            entry_price_spread = spread
            entry_time = dt
            entry_prices = (price1, price2)
        elif z < -z_entry:
            position = 1   # Long stock1, Short stock2
            entry_price_spread = spread
            entry_time = dt
            entry_prices = (price1, price2)

    elif position != 0:
        if (position == 1 and z >= z_exit) or (position == -1 and z <= -z_exit):
            exit_price_spread = spread
            exit_time = dt
            exit_prices = (price1, price2)
            spread_return = entry_price_spread - exit_price_spread
            qty = capital / (entry_prices[0] + abs(beta)*entry_prices[1])
            profit = qty * spread_return
            entries.append({
                'entry_time': entry_time,
                'type': 'Long' if position == 1 else 'Short',
                'entry_spread': entry_price_spread,
                'entry_price_1': entry_prices[0],
                'entry_price_2': entry_prices[1],
                'exit_time': exit_time,
                'exit_spread': exit_price_spread,
                'exit_price_1': exit_prices[0],
                'exit_price_2': exit_prices[1],
                'profit': profit
            })
            position = 0

# ---- Output Logs ----
log_df = pd.DataFrame(entries)

# ---- Plot ----
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data['zscore'], mode='lines', name='Z-score'))
fig.add_hline(y=z_entry, line=dict(color='red', dash='dot'))
fig.add_hline(y=-z_entry, line=dict(color='green', dash='dot'))
fig.add_hline(y=0, line=dict(color='gray'))
fig.update_layout(title='Z-score & Entry/Exit Thresholds')

# ---- Display ----
st.plotly_chart(fig, use_container_width=True)
st.subheader("📋 Strategy Log")
st.dataframe(log_df.round(3))

if not log_df.empty:
    total_profit = log_df['profit'].sum()
    st.success(f"Total Strategy Profit: ₹{total_profit:,.2f}")
    csv = log_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Log as CSV", csv, file_name='strategy_log.csv')
