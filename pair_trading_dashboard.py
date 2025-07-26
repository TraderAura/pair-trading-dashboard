import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from io import BytesIO
import plotly.graph_objs as go

st.set_page_config(layout="wide")
st.title("📈 Multi-Pair Trading Dashboard")

# --- Sidebar Options ---
timeframe = st.sidebar.selectbox("Select Timeframe", ["1mo", "3mo", "6mo"])
capital_per_pair = 100000

@st.cache_data(show_spinner=False)
def get_nifty100_tickers():
    # Simplified for this demo — you can update with actual NIFTY 100 list
    return [
        "HDFCBANK.NS", "INFY.NS", "RELIANCE.NS", "ICICIBANK.NS", "TCS.NS", "KOTAKBANK.NS",
        "ITC.NS", "LT.NS", "SBIN.NS", "HCLTECH.NS", "AXISBANK.NS", "WIPRO.NS", "SUNPHARMA.NS",
        "TECHM.NS", "MARUTI.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", "HINDUNILVR.NS",
        "POWERGRID.NS", "COALINDIA.NS"
    ]

@st.cache_data(show_spinner=False)
def fetch_price_data(tickers, period="3mo"):
    df = yf.download(tickers, period=period, interval="1d")
    return df["Close"].dropna(how="all")

# --- Step 1: Get Highly Correlated Pairs ---
tickers = get_nifty100_tickers()
prices = fetch_price_data(tickers, timeframe)
corr_matrix = prices.corr().abs()
pairs = []

for i in range(len(tickers)):
    for j in range(i + 1, len(tickers)):
        stock1, stock2 = tickers[i], tickers[j]
        corr = corr_matrix.loc[stock1, stock2]
        pairs.append((stock1, stock2, corr))

# Sort top 20 pairs
pairs_sorted = sorted(pairs, key=lambda x: x[2], reverse=True)[:20]

st.subheader("🔗 Top 20 Correlated Pairs")
st.dataframe(pd.DataFrame(pairs_sorted, columns=["Stock 1", "Stock 2", "Correlation"]))

# --- Step 2: Apply Pair Trading Strategy ---
ledger_records = []
summary = []

for stock1, stock2, corr in pairs_sorted:
    df1 = yf.download(stock1, period=timeframe, interval="1d")["Close"]
    df2 = yf.download(stock2, period=timeframe, interval="1d")["Close"]
    df = pd.concat([df1, df2], axis=1)
    df.columns = [stock1, stock2]
    df.dropna(inplace=True)
    
    df["Spread"] = df[stock1] - df[stock2]
    df["Z-Score"] = (df["Spread"] - df["Spread"].mean()) / df["Spread"].std()

    in_position = False
    entry_price_1 = entry_price_2 = 0
    quantity_1 = quantity_2 = 0
    pnl = 0
    
    for date, row in df.iterrows():
        z = row["Z-Score"]

        if not in_position and abs(z) > 1.5:
            # Entry
            in_position = True
            direction = "Long" if z < -1.5 else "Short"

            entry_price_1 = row[stock1]
            entry_price_2 = row[stock2]

            quantity_1 = capital_per_pair // entry_price_1
            quantity_2 = capital_per_pair // entry_price_2

            ledger_records.append({
                "Date": date,
                "Stock": stock1,
                "Side": "Buy" if z < -1.5 else "Sell",
                "Price": entry_price_1,
                "Qty": quantity_1,
                "Action": "Entry",
                "Z": z
            })
            ledger_records.append({
                "Date": date,
                "Stock": stock2,
                "Side": "Sell" if z < -1.5 else "Buy",
                "Price": entry_price_2,
                "Qty": quantity_2,
                "Action": "Entry",
                "Z": z
            })

        elif in_position and abs(z) <= 0.1:
            # Exit
            in_position = False
            exit_price_1 = row[stock1]
            exit_price_2 = row[stock2]

            # Reverse position
            ledger_records.append({
                "Date": date,
                "Stock": stock1,
                "Side": "Sell" if z < 0 else "Buy",
                "Price": exit_price_1,
                "Qty": quantity_1,
                "Action": "Exit",
                "Z": z
            })
            ledger_records.append({
                "Date": date,
                "Stock": stock2,
                "Side": "Buy" if z < 0 else "Sell",
                "Price": exit_price_2,
                "Qty": quantity_2,
                "Action": "Exit",
                "Z": z
            })

            # P&L calc
            pnl_1 = (exit_price_1 - entry_price_1) * quantity_1 * (1 if z < 0 else -1)
            pnl_2 = (entry_price_2 - exit_price_2) * quantity_2 * (1 if z < 0 else -1)
            net_pnl = pnl_1 + pnl_2 - 100  # ₹50 each leg
            pnl += net_pnl

    summary.append({"Pair": f"{stock1}/{stock2}", "Correlation": round(corr, 2), "P&L": round(pnl, 2)})

# --- Display Summary Table ---
st.subheader("📊 Strategy Summary")
st.dataframe(pd.DataFrame(summary).sort_values("P&L", ascending=False))

# --- Ledger Export ---
ledger_df = pd.DataFrame(ledger_records)
ledger_df["Date"] = ledger_df["Date"].dt.tz_localize(None)
output = BytesIO()
with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
    ledger_df.to_excel(writer, sheet_name="Ledger", index=False)
    pd.DataFrame(summary).to_excel(writer, sheet_name="Summary", index=False)
    processed = output.getvalue()

# CSV Export for Trade Ledger
st.download_button(
    label="📥 Download Trade Ledger as CSV",
    data=ledger.to_csv(index=False),
    file_name="trade_ledger.csv",
    mime="text/csv"
)

# CSV Export for P&L Summary
st.download_button(
    label="📥 Download P&L Summary as CSV",
    data=summary_df.to_csv(index=False),
    file_name="pnl_summary.csv",
    mime="text/csv"
)
