# CryptoCoinBuyerSystem

A simple Python backtesting script that compares two Bitcoin (BTC-USD) accumulation strategies over the last 10 years using `yfinance` and `pandas_ta`:

- Benchmark SIP: Buy $100 on the 1st of every month.
- Agentic Smart DCA: Daily RSI-based buys — $150 if RSI<30, $100 if 30≤RSI<40, $0 if RSI>70.

It prints a summary table (Total Invested, BTC Accumulated, Current Value, ROI %, Max Drawdown) and plots portfolio value over time.

## Setup

```bash
# From the project root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python src/backtest.py
```

## Dashboard (Streamlit)

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Use the UI to:
- Select symbol (`BTC-USD` or `BNB-USD`).
- Choose lookback window (1/3/5/10 years).
- Adjust RSI length and buy amounts.

## Notes
- Data is fetched from Yahoo Finance (`BTC-USD`), using adjusted close prices for calculations.
- RSI is computed with period 14 via `pandas_ta`.
- Max drawdown is computed from the equity curve as the minimum percentage drawdown from the running peak.
