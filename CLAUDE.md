# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install yfinance pandas matplotlib tabulate
```

Always maintain a `requirements.txt`. When adding a new dependency, append it there.

## Usage

```bash
python stock_analysis.py                    # default: AAPL
python stock_analysis.py TSLA              # single ticker
python stock_analysis.py AAPL MSFT GOOGL   # multiple tickers
```

Tickers are normalised to uppercase automatically. Output goes to `./stock_output/` (one `_technicals.csv`, one `_fundamentals.csv`, one `_chart.png` per ticker).

## Configuration

All indicator parameters are hardcoded constants at the top of `stock_analysis.py` (lines 31–44): `PERIOD`, `INTERVAL`, `SMA_SHORT`, `SMA_LONG`, `EMA_PERIOD`, `RSI_PERIOD`, `BB_PERIOD`, `BB_STD`, `MACD_FAST`, `MACD_SLOW`, `MACD_SIGNAL`, `OUTPUT_DIR`.

## Adding a technical indicator

Follow this four-part pattern every time:

1. **Compute function** — `add_<name>(df: pd.DataFrame, ...) -> pd.DataFrame` in the *Technical indicators* section. Write values into `df` columns and return `df`.
2. **Config constants** — add any period/threshold constants to the config block (lines 31–44) with inline comments.
3. **Wire into pipeline** — call the new function inside `compute_technicals()`.
4. **Outputs** — add a row to `tech_rows` in `print_summary()` and a new `gridspec` panel in `plot_analysis()`. Use the existing dark-theme palette (`#0d1117` background, `#e6edf3` primary, `#58a6ff` accent, `#f0883e` orange, `#3fb950` green, `#f85149` red).

## Code style

- Target Python 3.10+; use match/case and structural pattern matching where appropriate.
- Format and lint with `ruff`. Run `ruff check --fix .` and `ruff format .` before committing.
- Prefer type hints on all function signatures (`df: pd.DataFrame`, `-> pd.DataFrame`).
- No comments explaining *what* code does — only *why* when it would surprise a reader.

## Project direction

This is growing from a single-file script into a multi-file project. When adding significant new functionality (backtesting, strategy engine, portfolio tracking), split it into a proper module (`src/` or a package directory) rather than extending `stock_analysis.py` further. Propose the structure before implementing.
