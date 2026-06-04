# Stock Analysis

A Python CLI tool for technical and fundamental stock analysis. Fetches live data from Yahoo Finance and outputs a terminal summary, CSV exports, and dark-themed charts.

![AAPL chart example](stock_output/AAPL_chart.png)

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python stock_analysis.py                    # default: AAPL
python stock_analysis.py TSLA              # single ticker
python stock_analysis.py AAPL MSFT GOOGL   # multiple tickers
```

## Output

For each ticker, the script produces:

- **Terminal** — price, change, technical signals table, fundamentals table
- `stock_output/<TICKER>_technicals.csv` — daily OHLCV + all indicator values
- `stock_output/<TICKER>_fundamentals.csv` — P/E, EPS, margins, etc.
- `stock_output/<TICKER>_chart.png` — price/Bollinger/SMAs, volume, RSI, MACD

## Technical indicators

| Indicator | Parameters |
|-----------|-----------|
| SMA | 20, 50 |
| EMA | 20 |
| RSI | 14 |
| MACD | 12 / 26 / 9 |
| Bollinger Bands | 20, 2σ |

## Configuration

All indicator parameters are constants at the top of `stock_analysis.py`:

```python
PERIOD   = "1y"   # 1mo 3mo 6mo 1y 2y 5y
INTERVAL = "1d"   # 1d 1wk 1mo
SMA_SHORT = 20
SMA_LONG  = 50
# … etc.
```
