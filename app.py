import pandas as pd
import streamlit as st
import yfinance as yf

from stock_analysis import (
    SMA_LONG,
    SMA_SHORT,
    compute_technicals,
    get_fundamentals,
    macd_signal,
    make_figure,
    rsi_signal,
    sma_signal,
)

st.set_page_config(page_title="Stock Analysis", page_icon="📈", layout="wide")
st.title("📈 Stock Analysis")

with st.sidebar:
    st.header("Settings")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

col_input, col_btn = st.columns([4, 1])
with col_input:
    tickers_input = st.text_input("Tickers (comma-separated)", "AAPL", label_visibility="collapsed")
with col_btn:
    analyze = st.button("Analyze", type="primary", use_container_width=True)

if not analyze:
    st.stop()

tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

for symbol in tickers:
    with st.spinner(f"Fetching {symbol}…"):
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

    if df.empty:
        st.error(f"No data returned for '{symbol}'. Check the ticker symbol.")
        continue

    df = compute_technicals(df)
    fundamentals = get_fundamentals(ticker)

    last = df.iloc[-1]
    prev_close = df.iloc[-2]["Close"]
    price = last["Close"]
    chg = price - prev_close
    pct = chg / prev_close * 100

    st.subheader(symbol)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price", f"${price:.2f}", f"{pct:+.2f}%")
    m2.metric("RSI (14)", f"{last['RSI']:.1f}", rsi_signal(last["RSI"]))
    m3.metric(f"SMA {SMA_SHORT}", f"${last[f'SMA_{SMA_SHORT}']:.2f}")
    m4.metric(f"SMA {SMA_LONG}", f"${last[f'SMA_{SMA_LONG}']:.2f}")

    fig = make_figure(symbol, df)
    st.pyplot(fig, use_container_width=True)

    col_tech, col_fund = st.columns(2)

    with col_tech:
        st.write("**Technical Signals**")
        rsi = last["RSI"]
        st.dataframe(
            pd.DataFrame(
                {
                    "Indicator": ["RSI (14)", "MACD", f"SMA {SMA_SHORT}/{SMA_LONG}", "Bollinger Bands"],
                    "Value": [
                        f"{rsi:.1f}",
                        f"{last['MACD']:.3f}",
                        f"{last[f'SMA_{SMA_SHORT}']:.2f} / {last[f'SMA_{SMA_LONG}']:.2f}",
                        f"{last['BB_Lower']:.2f} – {last['BB_Upper']:.2f}",
                    ],
                    "Signal": [
                        rsi_signal(rsi),
                        macd_signal(last["MACD"], last["MACD_Signal"]),
                        sma_signal(price, last[f"SMA_{SMA_SHORT}"], last[f"SMA_{SMA_LONG}"]),
                        "",
                    ],
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    with col_fund:
        st.write("**Fundamentals**")
        st.dataframe(
            pd.DataFrame(fundamentals.items(), columns=["Metric", "Value"]),
            hide_index=True,
            use_container_width=True,
        )

    dl1, dl2 = st.columns(2)
    dl1.download_button(
        f"Download {symbol} Technicals CSV",
        df.to_csv().encode(),
        f"{symbol}_technicals.csv",
        "text/csv",
    )
    dl2.download_button(
        f"Download {symbol} Fundamentals CSV",
        pd.DataFrame(fundamentals.items(), columns=["Metric", "Value"]).to_csv(index=False).encode(),
        f"{symbol}_fundamentals.csv",
        "text/csv",
    )

    st.divider()
