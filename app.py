import streamlit as st
from pairs_trading import run_backtest
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Pair Trading Dashboard")
st.title("🔁 NIFTY 50 Pair Trading Dashboard")

st.sidebar.header("⚙️ Backtest Settings")
timeframe = st.sidebar.selectbox("Select Timeframe", ["1M", "3M", "6M"])
capital = st.sidebar.number_input("Capital per pair (₹)", value=100000, step=10000)

if st.sidebar.button("Run Backtest"):
    with st.spinner("Running backtest..."):
        results = run_backtest(timeframe, capital)
        st.success("Backtest completed!")

        for pair_result in results:
            st.subheader(f"📉 Pair: {pair_result['pair'][0]} / {pair_result['pair'][1]}")
            st.write("**Trade Summary:**", pair_result['summary'])
            st.dataframe(pair_result['trades'])

            fig = px.line(pair_result['equity_curve'], x='Date', y='Capital', title='Equity Curve')
            st.plotly_chart(fig, use_container_width=True)
