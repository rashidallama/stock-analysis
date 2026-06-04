---
name: run-analysis
description: Run stock analysis for one or more tickers. Use when asked to analyse a stock, check a ticker, or run the analysis script. Accepts ticker symbols as $ARGUMENTS.
disable-model-invocation: true
---

Run stock analysis for the requested tickers. $ARGUMENTS are the ticker symbols (space-separated); default to AAPL if none provided.

Steps:

1. **Check dependencies** — verify the required packages are installed:
   ```bash
   python -c "import yfinance, pandas, matplotlib, tabulate" 2>&1
   ```
   If any import fails, tell the user to run `pip install yfinance pandas matplotlib tabulate` and stop.

2. **Run the analysis**:
   ```bash
   python stock_analysis.py $ARGUMENTS
   ```

3. **Report results** — after the run completes, list the output files created in `./stock_output/` for each ticker (technicals CSV, fundamentals CSV, chart PNG). Note any tickers that failed with an error.
