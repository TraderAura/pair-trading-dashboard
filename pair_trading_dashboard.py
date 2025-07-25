import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# Sidebar inputs
nifty100_stocks = ["HDFCBANK.NS", "INFY.NS", "RELIANCE.NS", "TCS.NS", "ITC.NS"]
stock1 = st.sidebar.selectbox("Select Stock 1", options=nifty100_stocks, index=0)
stock2 = st.sidebar.selectbox("Select Stock 2", options=nifty100_stocks, index=1)
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-07-01"))
capital = st.sidebar.number_input("Starting Capital", value=100000)
interval = st.sidebar.selectbox("Timeframe", options=["1d", "1h", "15m"], index=0)

# Load Data
@st.cache_data
def load_data(stock1, stock2, start, end, interval):
    df1 = yf.download(stock1, start=start, end=end, interval=interval)["Close"]
    df2 = yf.download(stock2, start=start, end=end, interval=interval)["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [stock1, stock2]
    df.dropna(inplace=True)
    df.index = df.index.tz_localize(None)  # Remove timezone for Excel
    return df

data = load_data(stock1, stock2, start_date, end_date, interval)
st.subheader("📉 Price Chart")
st.line_chart(data)

# Spread and Z-Score
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# Z-Score & Spread plot
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data["Spread"], name="Spread"))
fig.add_trace(go.Scatter(x=data.index, y=data["Z-Score"], name="Z-Score", yaxis="y2"))
fig.update_layout(
    title="Spread and Z-Score",
    yaxis=dict(title="Spread"),
    yaxis2=dict(title="Z-Score", overlaying="y", side="right"),
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig, use_container_width=True)

# Trading logic
entry = None
trades = []
cash = capital
position_open = False

for i in range(1, len(data)):
    z = data["Z-Score"].iloc[i]
    prev_z = data["Z-Score"].iloc[i - 1]
    date = data.index[i]
    price1 = data[stock1].iloc[i]
    price2 = data[stock2].iloc[i]

    if not position_open:
        if z > 1.5:
            qty = cash // (price1 + price2)
            entry = {
                "type": "Short 1 / Long 2",
                "entry_time": date,
                "entry_z": z,
                "entry_price_1": price1,
                "entry_price_2": price2,
                "qty": qty
            }
            position_open = True

        elif z < -1.5:
            qty = cash // (price1 + price2)
            entry = {
                "type": "Long 1 / Short 2",
                "entry_time": date,
                "entry_z": z,
                "entry_price_1": price1,
                "entry_price_2": price2,
                "qty": qty
            }
            position_open = True

    elif position_open and abs(z) < 0.1:
        exit_price_1 = price1
        exit_price_2 = price2

        entry["exit_time"] = date
        entry["exit_price_1"] = exit_price_1
        entry["exit_price_2"] = exit_price_2
        entry["exit_z"] = z

        if entry["type"] == "Short 1 / Long 2":
            pnl = (entry["entry_price_1"] - exit_price_1 + exit_price_2 - entry["entry_price_2"]) * entry["qty"]
        else:
            pnl = (exit_price_1 - entry["entry_price_1"] + entry["entry_price_2"] - exit_price_2) * entry["qty"]

        entry["pnl"] = round(pnl, 2)
        cash += pnl
        trades.append(entry)
        entry = None
        position_open = False

# Trade Ledger Display
if trades:
    trade_df = pd.DataFrame(trades)
    st.subheader("📒 Trade P&L Ledger")
    st.dataframe(trade_df)

    total_pnl = trade_df["pnl"].sum()
    st.metric("💰 Total Strategy P&L", f"₹ {total_pnl:.2f}")
    st.metric("🏦 Final Capital", f"₹ {cash:.2f}")
else:
    st.info("No trades triggered for this pair in selected time period.")

# Excel Export
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="PriceData")
    if trades:
        trade_df.to_excel(writer, sheet_name="TradeLedger")
    writer.close()
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Excel Report",
    data=processed_data,
    file_name=f"{stock1}_{stock2}_Pair_Trading_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

