---
name: add-indicator
description: Add a new technical indicator to stock_analysis.py following the established pattern. Use when asked to implement a new indicator (e.g., Stochastic, ATR, OBV, Williams %R).
disable-model-invocation: false
---

When asked to add a technical indicator, follow these steps in order:

1. **Confirm the indicator spec**: Name the indicator, its inputs (period, thresholds), and formula. If ambiguous, ask one clarifying question before proceeding.

2. **Add config constants** to the config block in `stock_analysis.py` (after line 43, before the closing `─` line). Use ALL_CAPS with an inline comment explaining the parameter.

3. **Write the compute function** in the *Technical indicators* section (after the existing `add_bollinger` function). Signature: `add_<name>(df: pd.DataFrame, ...) -> pd.DataFrame`. Compute into named DataFrame columns and return `df`.

4. **Wire into `compute_technicals()`**: add the call after the existing `add_bollinger` call.

5. **Add a terminal row** in `print_summary()`: append a new entry to `tech_rows` with columns `[indicator_name, formatted_value, signal_string]`. Write a `<name>_signal(value) -> str` helper in the *Signal helpers* section if a signal makes sense (Oversold/Overbought/Neutral pattern).

6. **Add a chart panel** in `plot_analysis()`:
   - Increase `GridSpec` row count by 1 and add the new `height_ratio`.
   - Create a new `ax_<name>` subplot sharing the x-axis.
   - Apply the dark-theme style block (facecolor `#0d1117`, tick colors `gray`, spine color `#30363d`).
   - Plot using the existing palette: `#f0883e` orange for the main line, threshold lines in `#f85149` red / `#3fb950` green.
   - Hide x-tick labels on the new panel unless it's the bottom-most panel.

7. **Verify**: after writing the code, run `ruff check --fix stock_analysis.py && ruff format stock_analysis.py` to catch any style issues, then do a quick sanity check: `python stock_analysis.py AAPL` and confirm the new indicator appears in the terminal table and chart.
