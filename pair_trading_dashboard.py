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

# Dual-axis for Z-Score
fig.update_layout(
    title="Spread and Z-Score",
    yaxis=dict(title="Spread"),
    yaxis2=dict(title="Z-Score", overlaying="y", side="right"),
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig, use_container_width=True)

# Excel Export
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    data.to_excel(writer, sheet_name="PairData")
    writer.save()
    processed_data = output.getvalue()

st.download_button(
    label="📥 Download Data as Excel",
    data=processed_data,
    file_name=f"{stock1}_{stock2}_pair_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

