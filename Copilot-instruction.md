"""
Act as a Quantitative Developer. I need a Python backtesting script to compare two strategies for Bitcoin (BTC-USD) over the last 10 years using `yfinance`.

1. **Benchmark Strategy (SIP):** Buy $100 worth of BTC on the 1st of every month.
2. **Agentic Strategy (Smart DCA):** - Check Daily RSI (Relative Strength Index).
   - If RSI < 30 (Oversold): Buy $150 (Aggressive buy).
   - If RSI < 40 but > 30: Buy $100 (Normal buy).
   - If RSI > 70: Do not buy (Wait).
   - Trigger check frequency: Daily close.

Requirements:
- Use `pandas`, `yfinance`, and `pandas_ta` libraries.
- Calculate the total BTC accumulated and current Portfolio Value for both strategies.
- Calculate total invested capital for both.
- Print a summary table: Total Invested, Current Value, ROI %, Max Drawdown.
- Plot a line chart comparing "Portfolio Value Over Time" for both strategies using Matplotlib.
"""