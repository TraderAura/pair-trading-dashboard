import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from io import BytesIO

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# ✅ Predefined Stock Dropdowns (NIFTY 100 sample)
nifty100 = ["HDFCBANK.NS", "INFY.NS", "RELIANCE.NS", "ICICIBANK.NS", "TCS.NS", "SBIN.NS", "ITC.NS", "LT.NS"]

# Sidebar Inputs
stock1 = st.sidebar.selectbox("Select Stock 1", nifty100, index=0)
stock2 = st.sidebar.selectbox("Select Stock 2", nifty100, index=1)
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2024-07-01"))
interval = st.sidebar.selectbox("Select Interval", ["1d", "1h", "30m", "15m", "5m"], index=0)
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

# Spread & Z-score
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# 📈 Price Chart
st.subheader("🔹 Price Chart")
st.line_chart(data[[stock1, stock2]])

# 📉 Spread & Z-Score
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

# 📤 Excel Export
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="PairData")
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Excel",
    data=processed_data,
    file_name=f"{stock1}_{stock2}_pair_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
