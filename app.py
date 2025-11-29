import streamlit as st
import pandas as pd
from src.backtest import run_backtest, plot_portfolio_values
import matplotlib.pyplot as plt

st.set_page_config(page_title="Crypto Backtester", layout="wide")

st.title("Crypto DCA Backtester")
st.caption("Compare SIP vs RSI-based DCA vs News Sentiment DCA")

col1, col2, col3, col4 = st.columns(4)
with col1:
    symbol = st.selectbox("Symbol", options=["BTC-USD", "BNB-USD"], index=0)
with col2:
    lookback_label = st.selectbox("Lookback", options=["1M","3M","6M","1Y","3Y","5Y","10Y"], index=6)
with col3:
    rsi_length = st.number_input("RSI Length", min_value=2, max_value=50, value=14)
with col4:
    st.caption("1M≈30d, fractional years supported")

st.subheader("Strategy Parameters")
col4, col5, col6 = st.columns(3)
with col4:
    sip_amount = st.number_input("SIP Monthly Buy ($)", min_value=1.0, value=100.0)
with col5:
    agent_buy_low = st.number_input("Agent Buy if RSI<30 ($)", min_value=1.0, value=150.0)
with col6:
    agent_buy_normal = st.number_input("Agent Buy if 30≤RSI<40 ($)", min_value=1.0, value=100.0)

equal_budget = st.checkbox("Match SIP monthly budget for Agentic strategy", value=True)
include_news = st.checkbox("Include News Sentiment strategy", value=True)
use_real_news = st.checkbox("Use real news (CryptoCompare works without keys)", value=False)

if use_real_news:
    with st.expander("News Providers & API Keys"):
        st.success("CryptoCompare works immediately with no API key.")
        st.markdown("Optional keys to add more sources:")
        st.code("export COINMARKETCAP_API_KEY='your_key'\nexport CRYPTOPANIC_API_KEY='your_key'\nexport NEWSAPI_API_KEY='your_key'")
        st.markdown("- [CoinMarketCap](https://coinmarketcap.com/api/) — 10,000 req/month")
        st.markdown("- [CryptoPanic](https://cryptopanic.com/developers/api/) — limited free tier")
        st.markdown("- [NewsAPI](https://newsapi.org/) — 100 req/day, 30-day history")

run = st.button("Run Backtest")

if run:
    try:
        LOOKBACK_MAP = {"1M": 1/12, "3M": 3/12, "6M": 6/12, "1Y":1.0, "3Y":3.0, "5Y":5.0, "10Y":10.0}
        years_float = LOOKBACK_MAP.get(lookback_label, 1.0)
        summary, sip, agent, news = run_backtest(
            symbol=symbol,
            years=years_float,
            rsi_length=int(rsi_length),
            sip_amount=float(sip_amount),
            agent_buy_low=float(agent_buy_low),
            agent_buy_normal=float(agent_buy_normal),
            equal_monthly_budget=bool(equal_budget),
            include_news_strategy=bool(include_news),
            use_real_news=bool(use_real_news),
        )
        st.success("Backtest completed")
        st.subheader("Summary")
        st.dataframe(summary)

        st.subheader("Portfolio Value Over Time")
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(sip.value_series.index, sip.value_series.values, label='Benchmark SIP', linewidth=1.5)
        ax.plot(agent.value_series.index, agent.value_series.values, label='RSI-Based DCA', linewidth=1.5)
        if news is not None:
            ax.plot(news.value_series.index, news.value_series.values, label='News Sentiment DCA', linewidth=1.5)
        ax.set_title(f'Portfolio Value Over Time ({symbol})')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error running backtest: {e}")
        st.exception(e)

st.markdown("""
Notes:
- Data source: Yahoo Finance via yfinance.
- RSI computed using pandas_ta; default length 14.
- SIP buys run on first trading day each month; RSI agent buys evaluated daily at close.
- News Sentiment strategy can use real news from CryptoPanic/NewsAPI (requires API keys) or simulate sentiment from price momentum.
 - News Sentiment strategy can use real news from CryptoCompare (no key), CoinMarketCap (with key), CryptoPanic/NewsAPI (optional), or simulate sentiment from price momentum.
- TextBlob is used for sentiment analysis of news headlines.
""")