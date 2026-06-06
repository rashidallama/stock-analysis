from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

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


def _parse_num(val: str) -> float | None:
    """Parse formatted values like '$234.56', '3.5%', '1.23B' → float."""
    if not val or val == "N/A":
        return None
    try:
        v = str(val).replace("$", "").replace("%", "").replace(",", "").strip()
        if v.endswith("B"):
            return float(v[:-1]) * 1e9
        if v.endswith("M"):
            return float(v[:-1]) * 1e6
        return float(v)
    except (ValueError, AttributeError):
        return None


def build_commentary(
    symbol: str,
    price: float,
    pct: float,
    last,
    fundamentals: dict | None,
) -> str:
    score = 0
    bull: list[str] = []
    bear: list[str] = []

    rsi = last["RSI"]
    macd = last["MACD"]
    macd_sig = last["MACD_Signal"]
    sma_s = last[f"SMA_{SMA_SHORT}"]
    sma_l = last[f"SMA_{SMA_LONG}"]
    bb_upper = last["BB_Upper"]
    bb_lower = last["BB_Lower"]

    # ── RSI ───────────────────────────────────────────────────────────────────
    if rsi < 30:
        score += 2
        bull.append(
            f"RSI at {rsi:.1f} — deeply oversold, historically a mean-reversion entry"
        )
    elif rsi < 45:
        score += 1
        bull.append(f"RSI at {rsi:.1f} — momentum cooling, room to recover")
    elif rsi > 70:
        score -= 2
        bear.append(f"RSI at {rsi:.1f} — overbought, near-term pullback likely")
    elif rsi > 60:
        score -= 1
        bear.append(f"RSI at {rsi:.1f} — elevated, watch for reversal")

    # ── MACD ──────────────────────────────────────────────────────────────────
    if macd > macd_sig:
        score += 1
        bull.append("MACD above signal line — bullish momentum confirmed")
    else:
        score -= 1
        bear.append("MACD below signal line — bearish momentum")

    # ── SMA trend ─────────────────────────────────────────────────────────────
    if sma_s > sma_l and price > sma_s:
        score += 1
        bull.append(
            f"Price above both moving averages, SMA{SMA_SHORT} above SMA{SMA_LONG} — uptrend intact"
        )
    elif sma_s < sma_l and price < sma_s:
        score -= 1
        bear.append(
            f"Price below both moving averages, SMA{SMA_SHORT} below SMA{SMA_LONG} — downtrend"
        )

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    if price < bb_lower:
        score += 1
        bull.append("Price below lower Bollinger Band — statistically oversold")
    elif price > bb_upper:
        score -= 1
        bear.append("Price above upper Bollinger Band — statistically overbought")

    # ── Fundamentals ──────────────────────────────────────────────────────────
    analyst_target = None
    if fundamentals:
        rec = fundamentals.get("Recommendation", "N/A")
        if rec in ("BUY", "STRONG_BUY"):
            score += 2
            bull.append(f"Analyst consensus: {rec.replace('_', ' ')}")
        elif rec in ("SELL", "STRONG_SELL", "UNDERPERFORM"):
            score -= 1
            bear.append(f"Analyst consensus: {rec.replace('_', ' ')}")

        pe = _parse_num(fundamentals.get("P/E Ratio (TTM)"))
        if pe is not None:
            if pe < 0:
                score -= 1
                bear.append(
                    f"Negative P/E ({pe:.1f}x) — company unprofitable on a trailing basis"
                )
            elif pe < 15:
                score += 1
                bull.append(
                    f"P/E of {pe:.1f}x — attractively valued vs. market average"
                )
            elif pe > 50:
                score -= 1
                bear.append(f"P/E of {pe:.1f}x — stretched valuation")

        high_52 = _parse_num(fundamentals.get("52-Week High"))
        low_52 = _parse_num(fundamentals.get("52-Week Low"))
        if high_52 and low_52 and high_52 > low_52:
            pct_range = (price - low_52) / (high_52 - low_52) * 100
            if pct_range < 20:
                score += 1
                bull.append(f"Near 52-week low (${low_52:.2f}) — potential value entry")
            elif pct_range > 85:
                score -= 1
                bear.append(
                    f"Near 52-week high (${high_52:.2f}) — limited near-term upside"
                )

        analyst_target = _parse_num(fundamentals.get("Analyst Target"))

    # ── Verdict ───────────────────────────────────────────────────────────────
    if score >= 4:
        verdict = "🟢 BUY"
    elif score >= 2:
        verdict = "🟡 LEAN BUY"
    elif score <= -3:
        verdict = "🔴 SELL"
    elif score <= -1:
        verdict = "🟠 LEAN SELL"
    else:
        verdict = "⚪ HOLD"

    # ── Investment Thesis ─────────────────────────────────────────────────────
    primary = bull if score >= 0 else bear
    secondary = bear if score >= 0 else bull
    points = (primary[:2] + secondary[:1]) if primary else secondary[:2]
    if not points:
        points = ["Mixed signals across indicators — no clear directional edge."]
    thesis = "  \n".join(f"- {p}." for p in points)
    if analyst_target:
        upside = (analyst_target - price) / price * 100
        thesis += f"\n- Analyst consensus target ${analyst_target:.2f} implies {upside:+.1f}% from current price."

    # ── Entry Price ───────────────────────────────────────────────────────────
    if score >= 2:
        support = max(sma_s, bb_lower)
        gap = (price - support) / price
        if gap < 0.03:
            entry = f"**${price:.2f} (current)** — already at support; reasonable to enter now."
        else:
            entry = (
                f"**${support:.2f}–${price:.2f}** — enter at current levels or add on a "
                f"pullback to SMA{SMA_SHORT} support (${sma_s:.2f})."
            )
    elif score <= -2:
        entry = (
            f"**Avoid at ${price:.2f}.** Wait for RSI < 40 or a retest of "
            f"SMA{SMA_LONG} (${sma_l:.2f}) before considering entry."
        )
    else:
        entry = (
            f"**${sma_s:.2f}–${sma_l:.2f}** — wait for a pullback to moving average "
            "support before committing capital."
        )

    # ── MOAT ─────────────────────────────────────────────────────────────────
    moat = "Insufficient data to assess competitive position."
    if fundamentals:
        gm = _parse_num(fundamentals.get("Gross Margin"))
        roe = _parse_num(fundamentals.get("ROE"))
        if gm is not None:
            if gm > 60:
                moat_label, moat_desc = (
                    "Wide MOAT",
                    f"{gm:.1f}% gross margin signals strong pricing power and durable brand advantage",
                )
            elif gm > 35:
                moat_label, moat_desc = (
                    "Moderate MOAT",
                    f"{gm:.1f}% gross margin indicates some competitive advantage, but faces pricing pressure",
                )
            else:
                moat_label, moat_desc = (
                    "Narrow/No MOAT",
                    f"thin {gm:.1f}% gross margin points to a commoditized or highly competitive business",
                )
            roe_note = ""
            if roe is not None:
                if roe > 20:
                    roe_note = (
                        f" ROE of {roe:.1f}% confirms efficient capital deployment."
                    )
                elif roe > 10:
                    roe_note = f" ROE of {roe:.1f}% is adequate but not exceptional."
                else:
                    roe_note = f" ROE of {roe:.1f}% is weak — capital is not being deployed effectively."
            moat = f"**{moat_label}** — {moat_desc}.{roe_note}"

    # ── Key Risks ─────────────────────────────────────────────────────────────
    risks: list[str] = []

    for b in bear[:2]:
        risks.append(b)

    if fundamentals:
        de = _parse_num(fundamentals.get("Debt/Equity"))
        if de is not None and de > 150:
            risks.append(
                f"High debt/equity ({de:.0f}%) — elevated balance sheet risk if rates stay high"
            )
        nm = _parse_num(fundamentals.get("Net Margin"))
        if nm is not None and nm < 5:
            risks.append(
                f"Thin net margin ({nm:.1f}%) — vulnerable to cost inflation or revenue shortfalls"
            )

    if rsi > 55 and "RSI" not in " ".join(risks):
        risks.append(
            "Momentum-driven rally may unwind sharply on any negative catalyst"
        )
    if score >= 3:
        risks.append(
            "High expectations priced in — any earnings miss could trigger a sharp selloff"
        )
    if not risks:
        risks.append(
            "Macro/market risk — broad drawdowns affect all equities regardless of fundamentals"
        )
        risks.append(
            "Execution risk — company may miss analyst estimates or guide lower"
        )

    risk_block = "\n".join(f"- {r}" for r in risks[:3])

    # ── Assemble ──────────────────────────────────────────────────────────────
    return f"""## Verdict: {verdict}

### Why Invest (or Not)
{thesis}

### Entry Price
{entry}

### MOAT
{moat}

### Key Risks
{risk_block}"""


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
    try:
        df = ticker.history(period=period, interval=interval)
    except Exception:
        return None, None
    if df.empty:
        return None, None
    df = compute_technicals(df)
    try:
        fundamentals = get_fundamentals(ticker)
    except Exception:
        fundamentals = None
    return df, fundamentals


tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

for symbol in tickers:
    with st.spinner(f"Fetching {symbol}…"):
        df, fundamentals = fetch(symbol, period, interval)

    if df is None:
        st.error(
            f"**{symbol}:** Could not fetch data. Yahoo Finance may be rate-limiting — "
            "wait 30–60 seconds and try again, or check the ticker symbol."
        )
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

    # ── Investment Commentary ─────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 📋 Investment Analysis")
        commentary = build_commentary(symbol, price, pct, last, fundamentals)
        st.markdown(commentary)

    # ── Chart ─────────────────────────────────────────────────────────────────
    fig = make_plotly_figure(symbol, df)
    st.plotly_chart(fig, use_container_width=True)

    col_tech, col_fund = st.columns(2)

    with col_tech:
        st.write("**Technical Signals**")
        rsi_val = last["RSI"]
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
