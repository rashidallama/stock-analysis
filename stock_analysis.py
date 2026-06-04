#!/usr/bin/env python3
"""
Stock Analysis Script
─────────────────────
Technical analysis : SMA, EMA, RSI, MACD, Bollinger Bands
Fundamental analysis: P/E, EPS, market cap, revenue, margins
Output             : terminal summary, CSV export, matplotlib charts

Setup:
    pip install yfinance pandas matplotlib tabulate

Usage:
    python stock_analysis.py                      # default: AAPL
    python stock_analysis.py TSLA                 # single ticker
    python stock_analysis.py AAPL MSFT GOOGL      # multiple tickers
"""

import sys
import os
import warnings
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from tabulate import tabulate
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Configuration ─────────────────────────────────────────────────────────────
PERIOD = "1y"  # data window  : 1mo 3mo 6mo 1y 2y 5y
INTERVAL = "1d"  # bar size      : 1d 1wk 1mo
SMA_SHORT = 20  # short SMA period
SMA_LONG = 50  # long  SMA period
EMA_PERIOD = 20  # EMA period
RSI_PERIOD = 14  # RSI lookback
BB_PERIOD = 20  # Bollinger Band period
BB_STD = 2  # Bollinger Band std-dev multiplier
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
OUTPUT_DIR = "stock_output"  # folder for CSV + chart files
# ─────────────────────────────────────────────────────────────────────────────


# ── Technical indicators ──────────────────────────────────────────────────────


def add_sma(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df[f"SMA_{period}"] = df["Close"].rolling(window=period).mean()
    return df


def add_ema(df: pd.DataFrame, period: int) -> pd.DataFrame:
    df[f"EMA_{period}"] = df["Close"].ewm(span=period, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["RSI"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    return df


def add_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2) -> pd.DataFrame:
    sma = df["Close"].rolling(window=period).mean()
    rolling_std = df["Close"].rolling(window=period).std()
    df["BB_Upper"] = sma + std * rolling_std
    df["BB_Lower"] = sma - std * rolling_std
    df["BB_Mid"] = sma
    return df


def compute_technicals(df: pd.DataFrame) -> pd.DataFrame:
    df = add_sma(df, SMA_SHORT)
    df = add_sma(df, SMA_LONG)
    df = add_ema(df, EMA_PERIOD)
    df = add_rsi(df, RSI_PERIOD)
    df = add_macd(df, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    df = add_bollinger(df, BB_PERIOD, BB_STD)
    return df


# ── Signal helpers ────────────────────────────────────────────────────────────


def rsi_signal(rsi: float) -> str:
    if rsi < 30:
        return "Oversold  ⬆"
    if rsi > 70:
        return "Overbought ⬇"
    return "Neutral  ─"


def macd_signal(macd: float, signal: float) -> str:
    if macd > signal:
        return "Bullish  ▲"
    if macd < signal:
        return "Bearish  ▼"
    return "Neutral  ─"


def sma_signal(price: float, sma_short: float, sma_long: float) -> str:
    if sma_short > sma_long and price > sma_short:
        return "Bullish  ▲"
    if sma_short < sma_long and price < sma_short:
        return "Bearish  ▼"
    return "Neutral  ─"


# ── Fundamental helpers ───────────────────────────────────────────────────────


def fmt(val, prefix="", suffix="", decimals=2):
    """Format a number or return N/A."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    if isinstance(val, (int, float)):
        if abs(val) >= 1e9:
            return f"{prefix}{val / 1e9:.{decimals}f}B{suffix}"
        if abs(val) >= 1e6:
            return f"{prefix}{val / 1e6:.{decimals}f}M{suffix}"
        return f"{prefix}{val:.{decimals}f}{suffix}"
    return str(val)


def get_fundamentals(ticker_obj) -> dict:
    info = ticker_obj.info
    return {
        "Market Cap": fmt(info.get("marketCap"), prefix="$"),
        "P/E Ratio (TTM)": fmt(info.get("trailingPE")),
        "Forward P/E": fmt(info.get("forwardPE")),
        "EPS (TTM)": fmt(info.get("trailingEps"), prefix="$"),
        "Revenue (TTM)": fmt(info.get("totalRevenue"), prefix="$"),
        "Gross Margin": fmt(info.get("grossMargins"), suffix="%", decimals=1)
        if info.get("grossMargins") is None
        else f"{info['grossMargins'] * 100:.1f}%",
        "Net Margin": fmt(info.get("profitMargins"), suffix="%", decimals=1)
        if info.get("profitMargins") is None
        else f"{info['profitMargins'] * 100:.1f}%",
        "Debt/Equity": fmt(info.get("debtToEquity")),
        "ROE": fmt(info.get("returnOnEquity"), suffix="%")
        if info.get("returnOnEquity") is None
        else f"{info['returnOnEquity'] * 100:.1f}%",
        "Dividend Yield": "N/A"
        if not info.get("dividendYield")
        else f"{info['dividendYield'] * 100:.2f}%",
        "52-Week High": fmt(info.get("fiftyTwoWeekHigh"), prefix="$"),
        "52-Week Low": fmt(info.get("fiftyTwoWeekLow"), prefix="$"),
        "Analyst Target": fmt(info.get("targetMeanPrice"), prefix="$"),
        "Recommendation": info.get("recommendationKey", "N/A").upper(),
    }


# ── Terminal output ───────────────────────────────────────────────────────────


def print_summary(symbol: str, df: pd.DataFrame, fundamentals: dict) -> None:
    last = df.iloc[-1]
    price = last["Close"]
    prev = df.iloc[-2]["Close"]
    chg = price - prev
    pct = chg / prev * 100

    arrow = "▲" if chg >= 0 else "▼"
    color = "\033[92m" if chg >= 0 else "\033[91m"
    reset = "\033[0m"

    print(f"\n{'═' * 54}")
    print(
        f"  {symbol}  —  {color}{arrow} ${price:.2f}  ({chg:+.2f} / {pct:+.2f}%){reset}"
    )
    print(f"{'═' * 54}")

    # Technical signals
    rsi = last["RSI"]
    tech_rows = [
        ["RSI (14)", f"{rsi:.1f}", rsi_signal(rsi)],
        ["MACD", f"{last['MACD']:.3f}", macd_signal(last["MACD"], last["MACD_Signal"])],
        [
            f"SMA {SMA_SHORT}/{SMA_LONG}",
            f"{last[f'SMA_{SMA_SHORT}']:.2f} / {last[f'SMA_{SMA_LONG}']:.2f}",
            sma_signal(price, last[f"SMA_{SMA_SHORT}"], last[f"SMA_{SMA_LONG}"]),
        ],
        ["Bollinger Bands", f"{last['BB_Lower']:.2f} – {last['BB_Upper']:.2f}", ""],
    ]
    print("\n📈  Technical Signals")
    print(
        tabulate(
            tech_rows,
            headers=["Indicator", "Value", "Signal"],
            tablefmt="rounded_outline",
        )
    )

    # Fundamentals
    fund_rows = [[k, v] for k, v in fundamentals.items()]
    print("\n📊  Fundamentals")
    print(tabulate(fund_rows, headers=["Metric", "Value"], tablefmt="rounded_outline"))


# ── CSV export ────────────────────────────────────────────────────────────────


def save_csv(symbol: str, df: pd.DataFrame, fundamentals: dict, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    # Price + technicals
    price_path = os.path.join(out_dir, f"{symbol}_technicals.csv")
    df.to_csv(price_path)
    print(f"  ✔  Technicals saved → {price_path}")

    # Fundamentals
    fund_path = os.path.join(out_dir, f"{symbol}_fundamentals.csv")
    pd.DataFrame(fundamentals.items(), columns=["Metric", "Value"]).to_csv(
        fund_path, index=False
    )
    print(f"  ✔  Fundamentals saved → {fund_path}")


# ── Charts ────────────────────────────────────────────────────────────────────


def make_figure(symbol: str, df: pd.DataFrame) -> plt.Figure:
    fig = plt.figure(figsize=(14, 12), facecolor="#0d1117")
    fig.suptitle(f"{symbol} — Technical Analysis", color="white", fontsize=15, y=0.98)

    gs = gridspec.GridSpec(4, 1, figure=fig, hspace=0.08, height_ratios=[3, 1, 1, 1])

    ax_price = fig.add_subplot(gs[0])
    ax_vol = fig.add_subplot(gs[1], sharex=ax_price)
    ax_rsi = fig.add_subplot(gs[2], sharex=ax_price)
    ax_macd = fig.add_subplot(gs[3], sharex=ax_price)

    for ax in [ax_price, ax_vol, ax_rsi, ax_macd]:
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="gray")
        ax.yaxis.label.set_color("gray")
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

    idx = df.index

    # ── Price + Bollinger + SMAs ──────────────────────────────────────────────
    ax_price.fill_between(
        idx,
        df["BB_Lower"],
        df["BB_Upper"],
        alpha=0.12,
        color="#58a6ff",
        label="Bollinger Band",
    )
    ax_price.plot(idx, df["BB_Upper"], color="#58a6ff", linewidth=0.5, linestyle="--")
    ax_price.plot(idx, df["BB_Lower"], color="#58a6ff", linewidth=0.5, linestyle="--")
    ax_price.plot(idx, df["Close"], color="#e6edf3", linewidth=1.4, label="Price")
    ax_price.plot(
        idx,
        df[f"SMA_{SMA_SHORT}"],
        color="#f0883e",
        linewidth=1.2,
        label=f"SMA {SMA_SHORT}",
    )
    ax_price.plot(
        idx,
        df[f"SMA_{SMA_LONG}"],
        color="#3fb950",
        linewidth=1.2,
        label=f"SMA {SMA_LONG}",
    )
    ax_price.plot(
        idx,
        df[f"EMA_{EMA_PERIOD}"],
        color="#d2a8ff",
        linewidth=1.0,
        linestyle=":",
        label=f"EMA {EMA_PERIOD}",
    )
    ax_price.set_ylabel("Price (USD)", color="gray")
    ax_price.legend(
        loc="upper left",
        facecolor="#161b22",
        edgecolor="#30363d",
        labelcolor="white",
        fontsize=8,
    )
    plt.setp(ax_price.get_xticklabels(), visible=False)

    # ── Volume ────────────────────────────────────────────────────────────────
    colors = [
        "#3fb950" if c >= o else "#f85149" for c, o in zip(df["Close"], df["Open"])
    ]
    ax_vol.bar(idx, df["Volume"], color=colors, width=0.8, alpha=0.7)
    ax_vol.set_ylabel("Volume", color="gray")
    plt.setp(ax_vol.get_xticklabels(), visible=False)

    # ── RSI ───────────────────────────────────────────────────────────────────
    ax_rsi.plot(idx, df["RSI"], color="#f0883e", linewidth=1.2)
    ax_rsi.axhline(70, color="#f85149", linewidth=0.8, linestyle="--", alpha=0.7)
    ax_rsi.axhline(30, color="#3fb950", linewidth=0.8, linestyle="--", alpha=0.7)
    ax_rsi.fill_between(
        idx, df["RSI"], 70, where=(df["RSI"] >= 70), alpha=0.2, color="#f85149"
    )
    ax_rsi.fill_between(
        idx, df["RSI"], 30, where=(df["RSI"] <= 30), alpha=0.2, color="#3fb950"
    )
    ax_rsi.set_ylim(0, 100)
    ax_rsi.set_ylabel("RSI", color="gray")
    plt.setp(ax_rsi.get_xticklabels(), visible=False)

    # ── MACD ──────────────────────────────────────────────────────────────────
    ax_macd.plot(idx, df["MACD"], color="#58a6ff", linewidth=1.2, label="MACD")
    ax_macd.plot(idx, df["MACD_Signal"], color="#f0883e", linewidth=1.0, label="Signal")
    hist_colors = ["#3fb950" if v >= 0 else "#f85149" for v in df["MACD_Hist"]]
    ax_macd.bar(idx, df["MACD_Hist"], color=hist_colors, width=0.8, alpha=0.6)
    ax_macd.axhline(0, color="#30363d", linewidth=0.7)
    ax_macd.set_ylabel("MACD", color="gray")
    ax_macd.legend(
        loc="upper left",
        facecolor="#161b22",
        edgecolor="#30363d",
        labelcolor="white",
        fontsize=8,
    )
    ax_macd.tick_params(axis="x", colors="gray", labelsize=7)

    return fig


def plot_analysis(symbol: str, df: pd.DataFrame, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    fig = make_figure(symbol, df)
    chart_path = os.path.join(out_dir, f"{symbol}_chart.png")
    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)
    print(f"  ✔  Chart saved      → {chart_path}")


# ── Main ──────────────────────────────────────────────────────────────────────


def analyse(symbol: str) -> None:
    print(f"\n⏳  Fetching data for {symbol} …")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=PERIOD, interval=INTERVAL)

    if df.empty:
        print(f"  ✘  No data returned for '{symbol}'. Check the ticker symbol.")
        return

    df = compute_technicals(df)
    fundamentals = get_fundamentals(ticker)

    print_summary(symbol, df, fundamentals)

    print(f"\n💾  Saving outputs …")
    save_csv(symbol, df, fundamentals, OUTPUT_DIR)
    plot_analysis(symbol, df, OUTPUT_DIR)


def main() -> None:
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL"]
    tickers = [t.upper() for t in tickers]

    print(f"\n{'━' * 54}")
    print(f"  Stock Analysis  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Tickers: {', '.join(tickers)}")
    print(f"{'━' * 54}")

    for symbol in tickers:
        try:
            analyse(symbol)
        except Exception as e:
            print(f"  ✘  Error analysing {symbol}: {e}")

    print(f"\n✅  Done. Output files in ./{OUTPUT_DIR}/\n")


if __name__ == "__main__":
    main()
