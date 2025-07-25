import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# Sidebar Inputs
symbols = ["HDFCBANK.NS", "INFY.NS", "RELIANCE.NS", "TCS.NS", "ICICIBANK.NS"]
stock1 = st.sidebar.selectbox("Select Stock 1", symbols, index=0)
stock2 = st.sidebar.selectbox("Select Stock 2", symbols, index=1)
interval = st.sidebar.selectbox("Select Time Interval", ["1d", "1h", "15m"], index=0)
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-07-01"))
capital = st.sidebar.number_input("Starting Capital (₹)", value=100000)

# Load Data
@st.cache_data
def load_data(stock1, stock2, start, end, interval):
    df1 = yf.download(stock1, start=start, end=end, interval=interval)["Close"]
    df2 = yf.download(stock2, start=start, end=end, interval=interval)["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [stock1, stock2]
    df.dropna(inplace=True)
    return df

data = load_data(stock1, stock2, start_date, end_date, interval)
st.subheader("📉 Price Chart")
st.line_chart(data)

# Spread + Z-Score
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# Initialize trading variables
entry = None
trades = []
cash = capital
position_open = False

qty = 0

for i in range(1, len(data)):
    z = data["Z-Score"].iloc[i]
    prev_z = data["Z-Score"].iloc[i - 1]

    date = data.index[i]
    price1 = data[stock1].iloc[i]
    price2 = data[stock2].iloc[i]

    # Entry condition
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

    # Exit condition
    elif position_open and abs(z) < 0.1:
        exit_time = date
        exit_price_1 = price1
        exit_price_2 = price2
        entry["exit_time"] = exit_time
        entry["exit_price_1"] = exit_price_1
        entry["exit_price_2"] = exit_price_2
        entry["exit_z"] = z

        if entry["type"] == "Short 1 / Long 2":
            pnl = (entry["entry_price_1"] - exit_price_1 + exit_price_2 - entry["entry_price_2"]) * qty
        else:
            pnl = (exit_price_1 - entry["entry_price_1"] + entry["entry_price_2"] - exit_price_2) * qty

        entry["pnl"] = round(pnl, 2)
        cash += pnl
        trades.append(entry)
        position_open = False
        entry = None


# Plot Spread and Z-Score
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

# Step 3: Trade Signal Logic
position = None
entry_index = None
entry_z = entry_spread = 0
trades = []

for i in range(1, len(data)):
    z = data["Z-Score"].iloc[i]
    prev_z = data["Z-Score"].iloc[i - 1]

    # Entry
    if position is None:
        if z > 1.5:
            position = "Short Spread"
            entry_index = i
            entry_z = z
            entry_spread = data["Spread"].iloc[i]
        elif z < -1.5:
            position = "Long Spread"
            entry_index = i
            entry_z = z
            entry_spread = data["Spread"].iloc[i]

    # Exit
    elif position is not None and abs(z) < 0.05:  # close to zero
        exit_index = i
        exit_z = z
        exit_spread = data["Spread"].iloc[i]
        pnl = (entry_spread - exit_spread) if position == "Short Spread" else (exit_spread - entry_spread)

        trades.append({
            "Entry Time": data.index[entry_index],
            "Exit Time": data.index[exit_index],
            "Direction": position,
            "Entry Z": entry_z,
            "Exit Z": exit_z,
            "Entry Spread": entry_spread,
            "Exit Spread": exit_spread,
            "PnL (₹ spread points)": round(pnl, 2),
            "Duration": str(data.index[exit_index] - data.index[entry_index])
        })

        position = None  # reset

# Show trade log
if trades:
    trade_df = pd.DataFrame(trades)
    st.subheader("📋 Trade Log")
    st.dataframe(trade_df)
else:
    st.info("No trades were generated for the selected period and stocks.")

data.index = data.index.tz_localize(None)

if trades:
    for t in trades:
        t["Entry Time"] = t["Entry Time"].tz_localize(None)
        t["Exit Time"] = t["Exit Time"].tz_localize(None)
    trade_df = pd.DataFrame(trades)


# Excel Export
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="ZScoreData")
    if trades:
        trade_df.to_excel(writer, sheet_name="TradeLog", index=False)
    writer.close()
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Excel",
    data=processed_data,
    file_name="pair_trading_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
