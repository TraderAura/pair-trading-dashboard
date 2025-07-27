import yfinance as yf
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint
from scipy import stats
from datetime import datetime, timedelta

# Load NIFTY 50 stock list
def load_nifty50_symbols():
    df = pd.read_csv("nifty50_list.csv")
    return df["Symbol"].dropna().tolist()

# Get price data
def get_price_data(symbols, period="3mo", interval="1d"):
    data = yf.download(symbols, period=period, interval=interval, auto_adjust=True, progress=False)
    return data["Close"]

# Find cointegrated pairs
def find_cointegrated_pairs(data, significance=0.05):
    symbols = data.columns
    n = len(symbols)
    score_matrix = np.zeros((n, n))
    pvalue_matrix = np.ones((n, n))
    pairs = []

    for i in range(n):
        for j in range(i + 1, n):
            S1 = data[symbols[i]].dropna()
            S2 = data[symbols[j]].dropna()
            min_len = min(len(S1), len(S2))
            if min_len < 30:
                continue
            score, pvalue, _ = coint(S1[-min_len:], S2[-min_len:])
            pvalue_matrix[i, j] = pvalue
            if pvalue < significance:
                pairs.append((symbols[i], symbols[j], pvalue))

    pairs.sort(key=lambda x: x[2])  # sort by p-value
    return pairs[:10]  # top 10 pairs

# Z-score calculator
def get_zscore(spread):
    return (spread - spread.mean()) / spread.std()

# Backtest single pair
def backtest_pair(data, s1, s2, capital=100000):
    df = pd.DataFrame()
    df[s1] = data[s1]
    df[s2] = data[s2]
    df = df.dropna()

    spread = df[s1] - df[s2]
    zscore = get_zscore(spread)

    entry_z = 1.5
    exit_z = 0

    position = 0  # 1: long s1 short s2, -1: short s1 long s2, 0: no position
    capital_series = []
    trades = []
    cash = capital
    qty = 0
    entry_price = None

    for i in range(len(df)):
        date = df.index[i]
        z = zscore.iloc[i]
        price1 = df[s1].iloc[i]
        price2 = df[s2].iloc[i]

        # Entry
        if position == 0:
            if z > entry_z:
                qty = capital // (price1 + price2)
                entry_price = (price1, price2)
                position = -1  # short s1, long s2
                trades.append([date, "SELL", s1, price1, qty])
                trades.append([date, "BUY", s2, price2, qty])
            elif z < -entry_z:
                qty = capital // (price1 + price2)
                entry_price = (price1, price2)
                position = 1  # long s1, short s2
                trades.append([date, "BUY", s1, price1, qty])
                trades.append([date, "SELL", s2, price2, qty])

        # Exit
        elif position != 0 and abs(z) < exit_z:
            if position == 1:
                pnl = (price1 - entry_price[0]) * qty - (price2 - entry_price[1]) * qty
                trades.append([date, "SELL", s1, price1, qty])
                trades.append([date, "BUY", s2, price2, qty])
            elif position == -1:
                pnl = (entry_price[0] - price1) * qty - (entry_price[1] - price2) * qty
                trades.append([date, "BUY", s1, price1, qty])
                trades.append([date, "SELL", s2, price2, qty])
            cash += pnl
            position = 0

        capital_series.append([date, cash])

    equity_df = pd.DataFrame(capital_series, columns=["Date", "Capital"])
    trades_df = pd.DataFrame(trades, columns=["Date", "Action", "Stock", "Price", "Qty"])
    summary = {
        "Final Capital": round(cash, 2),
        "Return %": round(100 * (cash - capital) / capital, 2),
        "Trades": len(trades) // 2,
    }
    return equity_df, trades_df, summary

# Run the full backtest for top pairs
def run_backtest(timeframe, capital=100000):
    if timeframe == "1M":
        period = "1mo"
    elif timeframe == "3M":
        period = "3mo"
    else:
        period = "6mo"

    symbols = load_nifty50_symbols()
    data = get_price_data(symbols, period=period)

    top_pairs = find_cointegrated_pairs(data)
    results = []

    for s1, s2, pval in top_pairs:
        try:
            equity, trades, summary = backtest_pair(data, s1, s2, capital)
            results.append({
                "pair": (s1, s2),
                "pval": pval,
                "equity_curve": equity,
                "trades": trades,
                "summary": summary
            })
        except Exception as e:
            print(f"Error with pair {s1}/{s2}: {e}")
            continue

    return results
