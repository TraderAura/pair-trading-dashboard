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
    
    st.success("✅ Backtest completed!")
    st.markdown("---")

    for result in results:
        s1, s2 = result['pair']
        st.subheader(f"📊 {s1} / {s2} | p-value = {result['pval']:.4f}")
        
        # Equity Curve
        fig = px.line(result['equity_curve'], x='Date', y='Capital', title=f"📈 Equity Curve: {s1} / {s2}")
        st.plotly_chart(fig, use_container_width=True)

        # Trade Summary
        st.markdown("### 🧾 Summary")
        st.write(pd.DataFrame([result['summary']]))

        # Trade Log
        st.markdown("### 🔁 Trade Log")
        st.dataframe(result['trades'], use_container_width=True)

        st.markdown("---")
