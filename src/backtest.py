import datetime as dt
from dataclasses import dataclass
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import matplotlib.pyplot as plt
from textblob import TextBlob
import random


@dataclass
class PortfolioState:
    cash_invested: float
    btc_accumulated: float
    value_series: pd.Series


def fetch_btc_history(start: str, end: str, symbol: str = 'BTC-USD') -> pd.DataFrame:
    # Use Ticker.history for single-ticker with standard columns
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, auto_adjust=False)
    if df.empty:
        return df
    df = df.rename(columns={'Adj Close': 'Adj_Close'})
    if 'Adj_Close' not in df.columns and 'Close' in df.columns:
        df['Adj_Close'] = df['Close']
    df = df[['Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume']]
    df.index = pd.to_datetime(df.index)
    return df


def compute_rsi(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    rsi = ta.rsi(df['Adj_Close'], length=length)
    df = df.copy()
    df['RSI'] = rsi
    return df


def simulate_sip(df: pd.DataFrame, monthly_amount: float = 100.0) -> PortfolioState:
    # Buy on the 1st of every month at close price of that day (or next trading day if missing)
    df = df.copy()
    df['Month'] = df.index.to_period('M')

    # Identify first trading day per month
    first_days = df.groupby('Month').head(1).index
    buys = pd.Series(0.0, index=df.index)
    buys.loc[first_days] = monthly_amount

    btc_bought = buys / df['Adj_Close']
    btc_accumulated = btc_bought.cumsum()

    value_series = btc_accumulated * df['Adj_Close']
    cash_invested = buys.cumsum().iloc[-1]

    return PortfolioState(cash_invested=float(cash_invested), btc_accumulated=float(btc_accumulated.iloc[-1]), value_series=value_series)


def simulate_agentic_dca(df: pd.DataFrame) -> PortfolioState:
    # Daily checks at close. Amount per rules
    df = df.copy()
    df['Buy_USD'] = 0.0
    df.loc[df['RSI'] < 30, 'Buy_USD'] = 150.0
    df.loc[(df['RSI'] >= 30) & (df['RSI'] < 40), 'Buy_USD'] = 100.0
    df.loc[df['RSI'] > 70, 'Buy_USD'] = 0.0  # explicit for clarity

    btc_bought = df['Buy_USD'] / df['Adj_Close']
    btc_accumulated = btc_bought.cumsum()

    value_series = btc_accumulated * df['Adj_Close']
    cash_invested = df['Buy_USD'].sum()

    return PortfolioState(cash_invested=float(cash_invested), btc_accumulated=float(btc_accumulated.iloc[-1]), value_series=value_series)


def simulate_news_sentiment(df: pd.DataFrame) -> pd.Series:
    """
    Simulate news sentiment based on price momentum.
    In production, this would fetch real news headlines and analyze sentiment.
    Positive sentiment correlates with price increases; negative with decreases.
    Returns a sentiment score between -1 (very negative) and 1 (very positive).
    """
    # Calculate 7-day momentum as proxy for sentiment
    returns = df['Adj_Close'].pct_change(7)
    # Normalize to -1 to 1 range with some noise
    sentiment = returns.clip(-0.15, 0.15) / 0.15
    # Add random noise to simulate real news variability
    noise = pd.Series([random.gauss(0, 0.2) for _ in range(len(df))], index=df.index)
    sentiment = (sentiment + noise).clip(-1, 1)
    return sentiment


def simulate_news_based_dca(df: pd.DataFrame, monthly_budget: float = 100.0) -> PortfolioState:
    """
    News-based strategy: Buy on positive sentiment, hold on neutral, sell partial position on very negative.
    - Sentiment > 0.3: Buy aggressively
    - Sentiment 0 to 0.3: Buy normally
    - Sentiment -0.3 to 0: Hold (no buy)
    - Sentiment < -0.3: Sell 20% of holdings
    Monthly budget is allocated across trading days based on sentiment signals.
    """
    df = df.copy()
    df['Sentiment'] = simulate_news_sentiment(df)
    df['Month'] = df.index.to_period('M')
    
    # Initialize buy amounts per day
    df['Buy_USD'] = 0.0
    df.loc[df['Sentiment'] > 0.3, 'Buy_USD'] = 2.0  # Aggressive buy weight
    df.loc[(df['Sentiment'] >= 0) & (df['Sentiment'] <= 0.3), 'Buy_USD'] = 1.0  # Normal buy weight
    
    # Scale monthly to match budget
    def scale_month(group: pd.DataFrame) -> pd.DataFrame:
        total_weight = group['Buy_USD'].sum()
        if total_weight <= 0:
            # No signals, allocate to first day
            if len(group) > 0:
                group.at[group.index[0], 'Buy_USD'] = monthly_budget
            return group
        group['Buy_USD'] = (group['Buy_USD'] / total_weight) * monthly_budget
        return group
    
    df = df.groupby('Month', group_keys=False).apply(scale_month, include_groups=False)
    
    # Simulate portfolio with sells
    btc_holdings = 0.0
    cash_invested_total = 0.0
    cash_reserve = 0.0  # Cash from sells
    portfolio_values = []
    
    for idx, row in df.iterrows():
        # Buy
        buy_amount = row['Buy_USD']
        if buy_amount > 0:
            btc_bought = buy_amount / row['Adj_Close']
            btc_holdings += btc_bought
            cash_invested_total += buy_amount
        
        # Sell on very negative sentiment
        if row['Sentiment'] < -0.3 and btc_holdings > 0:
            sell_fraction = 0.2
            btc_to_sell = btc_holdings * sell_fraction
            sell_value = btc_to_sell * row['Adj_Close']
            btc_holdings -= btc_to_sell
            cash_reserve += sell_value
        
        portfolio_values.append(btc_holdings * row['Adj_Close'] + cash_reserve)
    
    value_series = pd.Series(portfolio_values, index=df.index)
    
    return PortfolioState(
        cash_invested=float(cash_invested_total),  # Net cash put in
        btc_accumulated=float(btc_holdings),
        value_series=value_series
    )


def max_drawdown(series: pd.Series) -> float:
    # Max drawdown as percentage
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return float(drawdown.min()) * 100.0


def summary_table(sip: PortfolioState, agent: PortfolioState, news: PortfolioState | None = None) -> pd.DataFrame:
    latest_sip = sip.value_series.iloc[-1]
    latest_agent = agent.value_series.iloc[-1]

    sip_roi = ((latest_sip - sip.cash_invested) / sip.cash_invested) * 100.0 if sip.cash_invested > 0 else 0.0
    agent_roi = ((latest_agent - agent.cash_invested) / agent.cash_invested) * 100.0 if agent.cash_invested > 0 else 0.0

    sip_mdd = max_drawdown(sip.value_series)
    agent_mdd = max_drawdown(agent.value_series)

    data = {
        'Strategy': ['Benchmark SIP', 'RSI-Based DCA'],
        'Total Invested ($)': [round(sip.cash_invested, 2), round(agent.cash_invested, 2)],
        'BTC Accumulated': [round(sip.btc_accumulated, 8), round(agent.btc_accumulated, 8)],
        'Current Value ($)': [round(latest_sip, 2), round(latest_agent, 2)],
        'ROI (%)': [round(sip_roi, 2), round(agent_roi, 2)],
        'Max Drawdown (%)': [round(sip_mdd, 2), round(agent_mdd, 2)],
    }
    
    if news is not None:
        latest_news = news.value_series.iloc[-1]
        news_roi = ((latest_news - news.cash_invested) / news.cash_invested) * 100.0 if news.cash_invested > 0 else 0.0
        news_mdd = max_drawdown(news.value_series)
        data['Strategy'].append('News Sentiment DCA')
        data['Total Invested ($)'].append(round(news.cash_invested, 2))
        data['BTC Accumulated'].append(round(news.btc_accumulated, 8))
        data['Current Value ($)'].append(round(latest_news, 2))
        data['ROI (%)'].append(round(news_roi, 2))
        data['Max Drawdown (%)'].append(round(news_mdd, 2))
    
    return pd.DataFrame(data)


def plot_portfolio_values(sip: PortfolioState, agent: PortfolioState, news: PortfolioState | None = None) -> None:
    plt.figure(figsize=(12, 6))
    plt.plot(sip.value_series.index, sip.value_series.values, label='Benchmark SIP', linewidth=1.5)
    plt.plot(agent.value_series.index, agent.value_series.values, label='RSI-Based DCA', linewidth=1.5)
    if news is not None:
        plt.plot(news.value_series.index, news.value_series.values, label='News Sentiment DCA', linewidth=1.5)
    plt.title('Portfolio Value Over Time (BTC-USD)')
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def run_backtest(symbol: str = 'BTC-USD', years: int = 10, rsi_length: int = 14,
                 sip_amount: float = 100.0,
                 agent_buy_low: float = 150.0,
                 agent_buy_normal: float = 100.0,
                 equal_monthly_budget: bool = False,
                 include_news_strategy: bool = False) -> tuple[pd.DataFrame, PortfolioState, PortfolioState, PortfolioState | None]:
    end = dt.date.today()
    start = end - dt.timedelta(days=int(years * 365 + 5))

    df = fetch_btc_history(start=start.isoformat(), end=end.isoformat(), symbol=symbol)
    if df.empty:
        raise RuntimeError(f'Failed to fetch {symbol} history from yfinance')

    df = compute_rsi(df, length=rsi_length)
    df = df.dropna(subset=['RSI', 'Adj_Close'])

    # Override agent amounts per parameters
    df_agent = df.copy()
    df_agent['Buy_USD'] = 0.0
    df_agent.loc[df_agent['RSI'] < 30, 'Buy_USD'] = agent_buy_low
    df_agent.loc[(df_agent['RSI'] >= 30) & (df_agent['RSI'] < 40), 'Buy_USD'] = agent_buy_normal
    df_agent.loc[df_agent['RSI'] > 70, 'Buy_USD'] = 0.0

    if equal_monthly_budget:
        # Constrain agent's monthly spend to equal SIP amount
        df_agent['Month'] = df_agent.index.to_period('M')
        # Compute scaling per month so total spend equals sip_amount
        def scale_month(group: pd.DataFrame) -> pd.DataFrame:
            total = group['Buy_USD'].sum()
            if total <= 0:
                # If no signals this month, allocate the budget to the first day
                if len(group) > 0:
                    group.at[group.index[0], 'Buy_USD'] = sip_amount
                return group
            scale = sip_amount / total
            group['Buy_USD'] = group['Buy_USD'] * scale
            return group
        df_agent = df_agent.groupby('Month', group_keys=False).apply(scale_month, include_groups=False)

    # Reuse simulate functions for consistency
    sip = simulate_sip(df, monthly_amount=sip_amount)
    # For agent, reuse value calc on df_agent
    btc_bought = df_agent['Buy_USD'] / df_agent['Adj_Close']
    btc_accumulated = btc_bought.cumsum()
    agent = PortfolioState(
        cash_invested=float(df_agent['Buy_USD'].sum()),
        btc_accumulated=float(btc_accumulated.iloc[-1]),
        value_series=btc_accumulated * df_agent['Adj_Close']
    )

    # News-based strategy
    news = None
    if include_news_strategy:
        news = simulate_news_based_dca(df, monthly_budget=sip_amount)
    
    summary = summary_table(sip, agent, news)
    return summary, sip, agent, news


def main():
    summary, sip, agent, news = run_backtest(symbol='BTC-USD', years=10, include_news_strategy=True)
    print('\nBacktest Summary (Last 10 Years)')
    print(summary.to_string(index=False))
    plot_portfolio_values(sip, agent, news)


if __name__ == '__main__':
    main()
