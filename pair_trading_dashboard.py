import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy import stats
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# Sidebar inputs
stock1 = st.sidebar.text_input("Enter Stock 1 Ticker", value="HDFCBANK.NS")
stock2 = st.sidebar.text_input("Enter Stock 2 Ticker", value="INFY.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-07-01"))
capital = st.sidebar.number_input("Starting Capital", value=100000)

# Load Data
@st.cache_data
def load_data(stock1, stock2, start, end):
    df1 = yf.download(stock1, start=start, end=end)["Close"]
    df2 = yf.download(stock2, start=start, end=end)["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [stock1, stock2]
    df.dropna(inplace=True)
    return df

data = load_data(stock1, stock2, start_date, end_date)
st.subheader("📉 Price Chart")
st.line_chart(data)

# Calculate Spread and Z-Score
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# Spread & Z-Score Plot
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

# --------------------------
# Z-score Strategy Backtest
# --------------------------
entry_z = 1.5
exit_z = 0
position = None
entry_price1 = entry_price2 = 0
trade_log = []
capital_live = capital

for i in range(len(data)):
    z = data["Z-Score"].iloc[i]
    date = data.index[i]
    price1 = data[stock1].iloc[i]
    price2 = data[stock2].iloc[i]

    if position is None:
        if z > entry_z:
            qty1 = capital_live // (2 * price1)
            qty2 = capital_live // (2 * price2)
            position = {
                "type": "Short Spread",
                "entry_index": i,
                "entry_date": date,
                "price1": price1,
                "price2": price2,
                "qty1": qty1,
                "qty2": qty2,
            }
        elif z < -entry_z:
            qty1 = capital_live // (2 * price1)
            qty2 = capital_live // (2 * price2)
            position = {
                "type": "Long Spread",
                "entry_index": i,
                "entry_date": date,
                "price1": price1,
                "price2": price2,
                "qty1": qty1,
                "qty2": qty2,
            }

    elif position is not None and abs(z) < exit_z:
        exit_price1 = price1
        exit_price2 = price2
        pnl = 0

        if position["type"] == "Short Spread":
            pnl = (position["price1"] - exit_price1) * position["qty1"] + \
                  (exit_price2 - position["price2"]) * position["qty2"]
        elif position["type"] == "Long Spread":
            pnl = (exit_price1 - position["price1"]) * position["qty1"] + \
                  (position["price2"] - exit_price2) * position["qty2"]

        capital_live += pnl
        trade_log.append({
            "Type": position["type"],
            "Entry Date": position["entry_date"],
            "Exit Date": date,
            "Entry Price1": position["price1"],
            "Exit Price1": exit_price1,
            "Entry Price2": position["price2"],
            "Exit Price2": exit_price2,
            "Qty1": position["qty1"],
            "Qty2": position["qty2"],
            "P&L": round(pnl, 2),
            "Capital After": round(capital_live, 2)
        })

        position = None

# --------------------------
# Trade Ledger Display
# --------------------------
ledger_df = pd.DataFrame(trade_log)

st.subheader("📒 Trade Ledger")
if not ledger_df.empty:
    st.dataframe(ledger_df)
    st.metric("Total Strategy P&L (₹)", f"{ledger_df['P&L'].sum():,.2f}")
    st.metric("Final Live Capital (₹)", f"{capital_live:,.2f}")
else:
    st.info("⚠️ No trades triggered in the selected range or thresholds.")

# --------------------------
# Excel Export (Price + Ledger)
# --------------------------
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="Price + Z-Score")
    ledger_df.to_excel(writer, sheet_name="Trade Ledger", index=False)
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Excel Report",
    data=processed_data,
    file_name=f"{stock1}_{stock2}_pair_trading_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
