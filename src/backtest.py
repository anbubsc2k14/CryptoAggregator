import datetime as dt
from dataclasses import dataclass
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import matplotlib.pyplot as plt


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


def max_drawdown(series: pd.Series) -> float:
    # Max drawdown as percentage
    roll_max = series.cummax()
    drawdown = (series - roll_max) / roll_max
    return float(drawdown.min()) * 100.0


def summary_table(sip: PortfolioState, agent: PortfolioState) -> pd.DataFrame:
    latest_sip = sip.value_series.iloc[-1]
    latest_agent = agent.value_series.iloc[-1]

    sip_roi = ((latest_sip - sip.cash_invested) / sip.cash_invested) * 100.0 if sip.cash_invested > 0 else 0.0
    agent_roi = ((latest_agent - agent.cash_invested) / agent.cash_invested) * 100.0 if agent.cash_invested > 0 else 0.0

    sip_mdd = max_drawdown(sip.value_series)
    agent_mdd = max_drawdown(agent.value_series)

    data = {
        'Strategy': ['Benchmark SIP', 'Agentic Smart DCA'],
        'Total Invested ($)': [round(sip.cash_invested, 2), round(agent.cash_invested, 2)],
        'BTC Accumulated': [round(sip.btc_accumulated, 8), round(agent.btc_accumulated, 8)],
        'Current Value ($)': [round(latest_sip, 2), round(latest_agent, 2)],
        'ROI (%)': [round(sip_roi, 2), round(agent_roi, 2)],
        'Max Drawdown (%)': [round(sip_mdd, 2), round(agent_mdd, 2)],
    }
    return pd.DataFrame(data)


def plot_portfolio_values(sip: PortfolioState, agent: PortfolioState) -> None:
    plt.figure(figsize=(12, 6))
    plt.plot(sip.value_series.index, sip.value_series.values, label='Benchmark SIP', linewidth=1.5)
    plt.plot(agent.value_series.index, agent.value_series.values, label='Agentic Smart DCA', linewidth=1.5)
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
                 equal_monthly_budget: bool = False) -> tuple[pd.DataFrame, PortfolioState, PortfolioState]:
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
        df_agent = df_agent.groupby('Month', group_keys=False).apply(scale_month)

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

    summary = summary_table(sip, agent)
    return summary, sip, agent


def main():
    summary, sip, agent = run_backtest(symbol='BTC-USD', years=10)
    print('\nBacktest Summary (Last 10 Years)')
    print(summary.to_string(index=False))
    plot_portfolio_values(sip, agent)


if __name__ == '__main__':
    main()
