import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy import stats
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard with P&L")

# Sidebar inputs
stock1 = st.sidebar.text_input("Enter Stock 1 Ticker", value="HDFCBANK.NS")
stock2 = st.sidebar.text_input("Enter Stock 2 Ticker", value="INFY.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-07-01"))
capital = st.sidebar.number_input("Starting Capital", value=100000)

@st.cache_data
def load_data(stock1, stock2, start, end):
    df1 = yf.download(stock1, start=start, end=end)["Close"]
    df2 = yf.download(stock2, start=start, end=end)["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [stock1, stock2]
    df.dropna(inplace=True)
    return df

data = load_data(stock1, stock2, start_date, end_date)
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# Price & Z-Score plot
st.subheader("📉 Price & Z-Score Chart")
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data["Spread"], name="Spread"))
fig.add_trace(go.Scatter(x=data.index, y=data["Z-Score"], name="Z-Score", yaxis="y2"))
fig.update_layout(
    yaxis=dict(title="Spread"),
    yaxis2=dict(title="Z-Score", overlaying="y", side="right"),
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig, use_container_width=True)

# Backtest with P&L tracking
trades = []
position = None  # None, "long", or "short"
entry_row = None
Q = 10000  # Use ₹10,000 per leg for now

for i in range(len(data)):
    z = data["Z-Score"].iloc[i]
    row = data.iloc[i]
    
    # Entry condition
    if position is None:
        if z > 1.5:
            position = "short"
            entry_row = row
            entry_time = data.index[i]
        elif z < -1.5:
            position = "long"
            entry_row = row
            entry_time = data.index[i]

    # Exit condition
    elif position and abs(z) < 0.05:
        exit_row = row
        exit_time = data.index[i]

        # Prices
        entry_price_1 = entry_row[stock1]
        entry_price_2 = entry_row[stock2]
        exit_price_1 = exit_row[stock1]
        exit_price_2 = exit_row[stock2]

        # Calculate qty
        qty1 = Q / entry_price_1
        qty2 = Q / entry_price_2

        if position == "long":
            pnl = (exit_price_1 - entry_price_1) * qty1 - (exit_price_2 - entry_price_2) * qty2
            trade_type = f"Long {stock1} / Short {stock2}"
        elif position == "short":
            pnl = (entry_price_2 - exit_price_2) * qty2 - (entry_price_1 - exit_price_1) * qty1
            trade_type = f"Short {stock1} / Long {stock2}"

        trades.append({
            "Entry Time": entry_time,
            "Exit Time": exit_time,
            "Trade Type": trade_type,
            f"Entry {stock1}": entry_price_1,
            f"Entry {stock2}": entry_price_2,
            f"Exit {stock1}": exit_price_1,
            f"Exit {stock2}": exit_price_2,
            "PnL": round(pnl, 2)
        })

        # Reset
        position = None
        entry_row = None

# Show P&L Table
if trades:
    trade_log = pd.DataFrame(trades)
    st.subheader("📄 Strategy P&L Log")
    st.dataframe(trade_log, use_container_width=True)

    total_profit = trade_log["PnL"].sum()
    st.success(f"💰 Total Strategy Profit: ₹{total_profit:.2f}")
else:
    st.warning("⚠️ No trades met the entry/exit conditions yet.")

# Excel export
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="Z-Score Data")
    if trades:
        trade_log.to_excel(writer, sheet_name="Trade Log", index=False)
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Excel Report",
    data=processed_data,
    file_name=f"{stock1}_{stock2}_strategy_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)




