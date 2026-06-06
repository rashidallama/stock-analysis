import anthropic
import pandas as pd
import streamlit as st
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from stock_analysis import (
    SMA_LONG,
    SMA_SHORT,
    compute_technicals,
    get_fundamentals,
    macd_signal,
    make_plotly_figure,
    rsi_signal,
    sma_signal,
)

_ANALYST_PROMPT = """You are an expert equity analyst with 20 years of experience across Wall Street and buy-side firms. Given a stock's technical indicators and fundamentals, produce a sharp, data-driven investment brief.

Respond in this exact format — no preamble, no disclaimers:

## Verdict: BUY / HOLD / SELL

### Why Invest (or Not)
2–3 sentences grounded in the numbers provided.

### Entry Price
Specific price point or range with a one-line rationale.

### MOAT
Competitive advantage (or lack of one) in 1–2 sentences.

### Key Risks
- Risk 1
- Risk 2
- Risk 3"""


@st.cache_data(ttl=3600, show_spinner=False)
def generate_commentary(
    symbol: str,
    price: float,
    pct: float,
    tech_str: str,
    fund_str: str,
) -> str:
    client = anthropic.Anthropic()
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": _ANALYST_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Analyze **{symbol}**\n\n"
                    f"Current price: ${price:.2f} ({pct:+.2f}% today)\n\n"
                    f"**Technical Indicators**\n{tech_str}\n\n"
                    f"**Fundamentals**\n{fund_str}"
                ),
            }
        ],
    ) as stream:
        message = stream.get_final_message()
    return next(b.text for b in message.content if b.type == "text")


st.set_page_config(page_title="Stock Analysis", page_icon="📈", layout="wide")
st.title("📈 Stock Analysis")

with st.sidebar:
    st.header("Settings")
    period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
    interval = st.selectbox("Interval", ["1d", "1wk", "1mo"], index=0)

col_input, col_btn = st.columns([4, 1])
with col_input:
    tickers_input = st.text_input(
        "Tickers (comma-separated)", "AAPL", label_visibility="collapsed"
    )
with col_btn:
    analyze = st.button("Analyze", type="primary", use_container_width=True)

if not analyze:
    st.stop()


@st.cache_data(ttl=300, show_spinner=False)
def fetch(symbol: str, period: str, interval: str):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        return None, None
    df = compute_technicals(df)
    try:
        fundamentals = get_fundamentals(ticker)
    except YFRateLimitError:
        fundamentals = None
    return df, fundamentals


tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

for symbol in tickers:
    with st.spinner(f"Fetching {symbol}…"):
        try:
            df, fundamentals = fetch(symbol, period, interval)
        except YFRateLimitError:
            st.error(
                f"**{symbol}:** Yahoo Finance is rate-limiting this IP. "
                "Wait 30–60 seconds and try again."
            )
            continue

    if df is None:
        st.error(f"No data returned for '{symbol}'. Check the ticker symbol.")
        continue

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

    # ── AI Investment Commentary ──────────────────────────────────────────────
    rsi_val = last["RSI"]
    tech_str = (
        f"RSI (14): {rsi_val:.1f} — {rsi_signal(rsi_val)}\n"
        f"MACD: {last['MACD']:.3f} — {macd_signal(last['MACD'], last['MACD_Signal'])}\n"
        f"SMA {SMA_SHORT}/{SMA_LONG}: {last[f'SMA_{SMA_SHORT}']:.2f} / {last[f'SMA_{SMA_LONG}']:.2f} — "
        f"{sma_signal(price, last[f'SMA_{SMA_SHORT}'], last[f'SMA_{SMA_LONG}'])}\n"
        f"Bollinger Bands: {last['BB_Lower']:.2f} – {last['BB_Upper']:.2f} (mid {last['BB_Mid']:.2f})"
    )
    fund_str = (
        "\n".join(f"{k}: {v}" for k, v in fundamentals.items())
        if fundamentals
        else "Fundamentals unavailable."
    )

    with st.container(border=True):
        st.markdown("#### 🤖 AI Investment Analysis")
        try:
            with st.spinner("Generating analysis…"):
                commentary = generate_commentary(symbol, price, pct, tech_str, fund_str)
            st.markdown(commentary)
        except anthropic.AuthenticationError:
            st.warning(
                "Add your `ANTHROPIC_API_KEY` to Streamlit secrets to enable AI commentary."
            )
        except anthropic.RateLimitError:
            st.warning("Claude API rate limit hit — try again in a moment.")
        except Exception as e:
            st.warning(f"AI commentary unavailable: {e}")

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = make_plotly_figure(symbol, df)
    st.plotly_chart(fig, use_container_width=True)

    col_tech, col_fund = st.columns(2)

    with col_tech:
        st.write("**Technical Signals**")
        st.dataframe(
            pd.DataFrame(
                {
                    "Indicator": [
                        "RSI (14)",
                        "MACD",
                        f"SMA {SMA_SHORT}/{SMA_LONG}",
                        "Bollinger Bands",
                    ],
                    "Value": [
                        f"{rsi_val:.1f}",
                        f"{last['MACD']:.3f}",
                        f"{last[f'SMA_{SMA_SHORT}']:.2f} / {last[f'SMA_{SMA_LONG}']:.2f}",
                        f"{last['BB_Lower']:.2f} – {last['BB_Upper']:.2f}",
                    ],
                    "Signal": [
                        rsi_signal(rsi_val),
                        macd_signal(last["MACD"], last["MACD_Signal"]),
                        sma_signal(
                            price, last[f"SMA_{SMA_SHORT}"], last[f"SMA_{SMA_LONG}"]
                        ),
                        "",
                    ],
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    with col_fund:
        if fundamentals:
            st.write("**Fundamentals**")
            st.dataframe(
                pd.DataFrame(fundamentals.items(), columns=["Metric", "Value"]),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.warning(
                "Fundamentals unavailable (rate limited). Try again in a moment."
            )

    dl1, dl2 = st.columns(2)
    dl1.download_button(
        f"Download {symbol} Technicals CSV",
        df.to_csv().encode(),
        f"{symbol}_technicals.csv",
        "text/csv",
    )
    if fundamentals:
        dl2.download_button(
            f"Download {symbol} Fundamentals CSV",
            pd.DataFrame(fundamentals.items(), columns=["Metric", "Value"])
            .to_csv(index=False)
            .encode(),
            f"{symbol}_fundamentals.csv",
            "text/csv",
        )

    st.divider()
