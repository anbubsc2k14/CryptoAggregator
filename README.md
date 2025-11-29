# CryptoCoinBuyerSystem

A Python backtesting system that compares three Bitcoin/BNB accumulation strategies using `yfinance`, `pandas_ta`, and sentiment analysis:

- Benchmark SIP: Buy $100 on the 1st of every month.
- RSI-Based DCA: Daily RSI-based buys — $150 if RSI<30, $100 if 30≤RSI<40, $0 if RSI>70.
- News Sentiment DCA: Buys/holds/sells based on simulated news sentiment (momentum-based proxy).

The dashboard prints a summary table (Total Invested, Crypto Accumulated, Current Value, ROI %, Max Drawdown) and plots portfolio value over time for all strategies.

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
- Enable/disable News Sentiment strategy for comparison.
- Match monthly budgets across all strategies for fair ROI comparison.

## Real News Integration

The system supports fetching real cryptocurrency news from:
- **CryptoPanic**: Crypto-specific news aggregator
- **NewsAPI**: General news including crypto

See [API_KEYS.md](API_KEYS.md) for setup instructions.

Without API keys, the system falls back to simulating sentiment from price momentum.

## Notes
- Data is fetched from Yahoo Finance (`BTC-USD`), using adjusted close prices for calculations.
- RSI is computed with period 14 via `pandas_ta`.
- Max drawdown is computed from the equity curve as the minimum percentage drawdown from the running peak.
- News Sentiment strategy uses TextBlob for sentiment analysis of real news headlines, or falls back to price momentum simulation.
