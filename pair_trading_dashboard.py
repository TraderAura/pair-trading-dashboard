import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import itertools

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("📊 NIFTY 50 Pair Trading Backtest Dashboard")

# Upload NIFTY50 CSV (you already did)
nifty50_df = pd.read_csv("ind_nifty50list.csv")
nifty50_df['YahooSymbol'] = nifty50_df['Symbol'].str.upper().str.strip() + ".NS"
nifty_symbols = nifty50_df['YahooSymbol'].tolist()

# Timeframe selection
timeframe = st.selectbox("Select Timeframe", ["1 Month", "3 Months"])
end_date = datetime.today()
if timeframe == "1 Month":
    start_date = end_date - timedelta(days=30)
elif timeframe == "3 Months":
    start_date = end_date - timedelta(days=90)

# --- Function to fetch and merge two stock prices ---
@st.cache_data(show_spinner=False)
def fetch_pair_data(ticker1, ticker2, start, end):
    df1 = yf.download(ticker1, start=start, end=end)['Close']
    df2 = yf.download(ticker2, start=start, end=end)['Close']
    df = pd.concat([df1, df2], axis=1)
    df.columns = [ticker1, ticker2]
    df.dropna(inplace=True)
    return df

# --- Function to compute correlation matrix ---
@st.cache_data(show_spinner=False)
def compute_top_correlated_pairs(symbols, start, end, top_n=20):
    price_data = yf.download(symbols, start=start, end=end)['Close']
    price_data = price_data.dropna(axis=1)
    corr_matrix = price_data.corr().abs()
    upper_triangle = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    sorted_pairs = (
        upper_triangle.stack()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={0: 'Correlation', 'level_0': 'Stock1', 'level_1': 'Stock2'})
    )
    return sorted_pairs.head(top_n)

# --- Backtest Z-score strategy ---
def run_backtest(df, stock1, stock2, capital=100000):
    df['Spread'] = df[stock1] - df[stock2]
    df['Z'] = (df['Spread'] - df['Spread'].mean()) / df['Spread'].std()

    position = 0  # -1 = Short Spread, 1 = Long Spread, 0 = Neutral
    entry_price1, entry_price2 = 0, 0
    trades = []
    cash = capital
    for i in range(1, len(df)):
        z = df['Z'].iloc[i]
        date = df.index[i]

        if position == 0:
            if z > 1.5:
                entry_price1 = df[stock1].iloc[i]
                entry_price2 = df[stock2].iloc[i]
                qty = cash // (entry_price1 + entry_price2)
                position = -1  # Short stock1, Long stock2
                trades.append([date, "Enter Short", stock1, entry_price1, stock2, entry_price2, qty])

            elif z < -1.5:
                entry_price1 = df[stock1].iloc[i]
                entry_price2 = df[stock2].iloc[i]
                qty = cash // (entry_price1 + entry_price2)
                position = 1  # Long stock1, Short stock2
                trades.append([date, "Enter Long", stock1, entry_price1, stock2, entry_price2, qty])

        elif position == 1 and z >= 0:
            exit_price1 = df[stock1].iloc[i]
            exit_price2 = df[stock2].iloc[i]
            pnl = (exit_price1 - entry_price1 - (exit_price2 - entry_price2)) * qty
            cash += pnl
            trades.append([date, "Exit Long", stock1, exit_price1, stock2, exit_price2, qty, pnl])
            position = 0

        elif position == -1 and z <= 0:
            exit_price1 = df[stock1].iloc[i]
            exit_price2 = df[stock2].iloc[i]
            pnl = (entry_price1 - exit_price1 - (entry_price2 - exit_price2)) * qty
            cash += pnl
            trades.append([date, "Exit Short", stock1, exit_price1, stock2, exit_price2, qty, pnl])
            position = 0

    trades_df = pd.DataFrame(trades, columns=["Date", "Action", "Stock1", "Price1", "Stock2", "Price2", "Qty", "PnL"])
    total_return = cash - capital
    sharpe = total_return / (np.std(trades_df['PnL'].dropna()) + 1e-6)
    drawdown = trades_df['PnL'].cumsum().cummax() - trades_df['PnL'].cumsum()
    max_drawdown = drawdown.max()

    return trades_df, total_return, sharpe, max_drawdown

# --- Main Execution ---
top_pairs_df = compute_top_correlated_pairs(nifty_symbols, start_date, end_date, top_n=20)
st.subheader("Top 20 Correlated Pairs")
st.dataframe(top_pairs_df)

summary = []
with st.spinner("🔁 Running backtests on pairs..."):
    for idx, row in top_pairs_df.iterrows():
        s1, s2 = row['Stock1'], row['Stock2']
        df = fetch_pair_data(s1, s2, start_date, end_date)
        if len(df) < 30:
            continue
        trades, ret, sharpe, dd = run_backtest(df, s1, s2)
        summary.append({
            "Pair": f"{s1}/{s2}",
            "Total Return": round(ret, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Max Drawdown": round(dd, 2),
            "Trades": len(trades) // 2
        })

summary_df = pd.DataFrame(summary)
st.subheader("Backtest Summary")
st.dataframe(summary_df.sort_values(by="Total Return", ascending=False), use_container_width=True)
