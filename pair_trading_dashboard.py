import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objs as go

st.set_page_config(layout="wide")
st.title("🔍 Auto-Scan Top 20 Correlated NIFTY100 Pairs (Recent Data)")

# ----- Sidebar Controls -----
timeframe_option = st.sidebar.selectbox(
    "Select Timeframe for Correlation",
    ("1 Month", "3 Months", "6 Months")
)

capital_per_pair = st.sidebar.number_input("Capital per Pair (₹)", value=100000)

# Timeframe logic
today = datetime.today()
if timeframe_option == "1 Month":
    start_date = today - timedelta(days=30)
elif timeframe_option == "3 Months":
    start_date = today - timedelta(days=90)
else:
    start_date = today - timedelta(days=180)

end_date = today

# ----- Load NIFTY 100 symbols -----
nifty_100 = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS",
    "SBIN.NS", "AXISBANK.NS", "LT.NS", "ITC.NS", "HINDUNILVR.NS", "BHARTIARTL.NS",
    "ASIANPAINT.NS", "MARUTI.NS", "HCLTECH.NS", "ULTRACEMCO.NS", "WIPRO.NS", "SUNPHARMA.NS",
    "NTPC.NS", "POWERGRID.NS", "NESTLEIND.NS", "BAJFINANCE.NS", "ADANIENT.NS", "ADANIPORTS.NS",
    "CIPLA.NS", "DIVISLAB.NS", "BPCL.NS", "IOC.NS", "HINDALCO.NS", "COALINDIA.NS",
    "TITAN.NS", "TECHM.NS", "BRITANNIA.NS", "JSWSTEEL.NS", "BAJAJFINSV.NS", "EICHERMOT.NS",
    "GRASIM.NS", "SHREECEM.NS", "UPL.NS", "ONGC.NS", "DRREDDY.NS", "BAJAJ-AUTO.NS",
    "HEROMOTOCO.NS", "SBILIFE.NS", "HDFCLIFE.NS", "ICICIPRULI.NS", "TATACONSUM.NS", "INDUSINDBK.NS"
]

# ----- Download historical data -----
@st.cache_data(show_spinner=True)
def fetch_price_data(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, interval="1d")["Close"]
    return data.dropna(axis=1, how="any")  # Remove tickers with missing data

st.info("📥 Downloading recent price data...")
price_data = fetch_price_data(nifty_100, start_date, end_date)

# ----- Calculate Correlation -----
st.success("✅ Data ready. Calculating correlations...")

correlation_matrix = price_data.corr()
pairs = []
tickers = correlation_matrix.columns

for i in range(len(tickers)):
    for j in range(i+1, len(tickers)):
        corr = correlation_matrix.iloc[i, j]
        pairs.append({
            "Stock 1": tickers[i],
            "Stock 2": tickers[j],
            "Correlation": corr
        })

# ----- Top 20 Most Correlated Pairs -----
top_pairs = sorted(pairs, key=lambda x: abs(x["Correlation"]), reverse=True)[:20]
df_top = pd.DataFrame(top_pairs)
df_top["Capital Allocated (₹)"] = capital_per_pair

st.subheader(f"📊 Top 20 Correlated Pairs - {timeframe_option}")
st.dataframe(df_top, use_container_width=True)

# 📥 Option to export
st.download_button(
    label="📥 Download as Excel",
    data=df_top.to_csv(index=False),
    file_name=f"Top_Correlated_Pairs_{timeframe_option.replace(' ', '')}.csv",
    mime="text/csv"
)
