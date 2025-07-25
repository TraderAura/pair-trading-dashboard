
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy import stats

st.set_page_config(layout="wide")
st.title("📈 Custom Pair Trading Dashboard")

# Select stocks
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
    return pd.DataFrame({stock1: df1, stock2: df2})

data = load_data(stock1, stock2, start_date, end_date)
st.subheader("Price Chart")
st.line_chart(data)

# Z-score calculation
data["Spread"] = data[stock1] - data[stock2]
data["Z-Score"] = (data["Spread"] - data["Spread"].mean()) / data["Spread"].std()

# Plot Spread + Z-Score
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data["Spread"], name="Spread"))
fig.add_trace(go.Scatter(x=data.index, y=data["Z-Score"], name="Z-Score"))
st.plotly_chart(fig, use_container_width=True)

# Excel export
st.download_button(
    label="📥 Download Data as Excel",
    data=data.to_excel(index=True),
    file_name="pair_trading_data.xlsx"
)
