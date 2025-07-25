import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy import stats
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# Sidebar: stock selection and settings
stock_options = ["HDFCBANK.NS", "INFY.NS", "RELIANCE.NS", "TCS.NS", "ICICIBANK.NS"]
stock1 = st.sidebar.selectbox("Stock 1", stock_options, index=0)
stock2 = st.sidebar.selectbox("Stock 2", stock_options, index=1)
interval = st.sidebar.selectbox("Time Interval", ["1d", "1h", "30m", "15m", "5m"], index=0)
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-07-01"))
capital = st.sidebar.number_input("Starting Capital (₹)", value=100000)

# Load data
@st.cache_data
def load_data(stock1, stock2, start, end, interval):
    df1 = yf.download(stock1, start=start, end=end, interval=interval)["Close"]
    df2 = yf.download(stock2, start=start, end=end, interval=interval)["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [stock1, stock2]
    df.dropna(inplace=True)
    return df

data = load_data(stock1, stock2, start_date, end_date, interval)

# Plot price chart
st.subheader("📉 Price Chart")
st.line_chart(data)

# Z-score and spread
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# Trade logic
in_position = False
entry_index = None
ledger = []
current_cash = capital

for i in range(len(data)):
    z = data["Z-Score"].iloc[i]
    price1 = data[stock1].iloc[i]
    price2 = data[stock2].iloc[i]
    timestamp = data.index[i]

    # Entry Condition
    if not in_position and abs(z) > 1.5:
        entry_index = i
        entry_price1 = price1
        entry_price2 = price2
        direction = "Short 1, Long 2" if z > 1.5 else "Short 2, Long 1"
        qty1 = qty2 = current_cash // (2 * max(entry_price1, entry_price2))
        in_position = True

    # Exit Condition
    elif in_position and abs(z) < 0.1:
        exit_price1 = price1
        exit_price2 = price2
        trade_date = data.index[i]

        # Determine P&L based on trade direction
        if direction == "Short 1, Long 2":
            pnl = (entry_price1 - exit_price1) * qty1 + (exit_price2 - entry_price2) * qty2
        else:
            pnl = (entry_price2 - exit_price2) * qty2 + (exit_price1 - entry_price1) * qty1

        # Update cash
        current_cash += pnl - 100  # ₹50 cost per leg
        ledger.append({
            "Date": trade_date.replace(tzinfo=None),
            "Direction": direction,
            "Entry Price 1": entry_price1,
            "Exit Price 1": exit_price1,
            "Entry Price 2": entry_price2,
            "Exit Price 2": exit_price2,
            "Qty1": qty1,
            "Qty2": qty2,
            "P&L": pnl,
            "Cash After Trade": current_cash
        })

        in_position = False
        entry_index = None

# Plot spread + z-score
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

# Broker-style ledger
ledger_df = pd.DataFrame(ledger)

if not ledger_df.empty:
    st.subheader("📒 Broker-Style Ledger")
    st.dataframe(ledger_df.style.format({
        "Entry Price 1": "{:.2f}", "Exit Price 1": "{:.2f}",
        "Entry Price 2": "{:.2f}", "Exit Price 2": "{:.2f}",
        "Qty1": "{:.0f}", "Qty2": "{:.0f}",
        "P&L": "₹{:.2f}", "Cash After Trade": "₹{:.2f}"
    }), use_container_width=True)

    st.markdown(f"### 💼 Final Capital: ₹{round(current_cash, 2):,.2f}")
else:
    st.info("No trades executed yet within selected time range.")

# Excel download
output = BytesIO()
data.index = data.index.tz_localize(None)  # Remove timezone for Excel
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="Price + Z")
    if not ledger_df.empty:
        ledger_df.to_excel(writer, sheet_name="Trade Ledger", index=False)
    writer.close()
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Excel Report",
    data=processed_data,
    file_name=f"{stock1}_{stock2}_pair_trading_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
