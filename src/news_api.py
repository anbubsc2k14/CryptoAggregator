import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
from typing import Optional
import time


class NewsAPIClient:
    """Fetch crypto news from CryptoPanic and NewsAPI"""
    
    def __init__(self):
        self.cryptopanic_key = os.getenv('CRYPTOPANIC_API_KEY', '')
        self.newsapi_key = os.getenv('NEWSAPI_API_KEY', '')
        self.cache = {}
    
    def fetch_cryptopanic_news(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch news from CryptoPanic API.
        Free tier: 100 requests/day
        """
        if not self.cryptopanic_key:
            return pd.DataFrame()
        
        # Extract coin symbol (BTC, BNB, ETH, etc.)
        coin = symbol.split('-')[0]
        
        news_list = []
        current = start_date
        
        while current <= end_date:
            cache_key = f"cp_{coin}_{current.date()}"
            if cache_key in self.cache:
                news_list.extend(self.cache[cache_key])
                current += timedelta(days=1)
                continue
            
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': self.cryptopanic_key,
                'currencies': coin,
                'filter': 'important',  # Only important news
                'public': 'true'
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('results', []):
                        news_list.append({
                            'date': pd.to_datetime(item['published_at']),
                            'title': item['title'],
                            'source': 'CryptoPanic'
                        })
                    self.cache[cache_key] = data.get('results', [])
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"CryptoPanic API error: {e}")
                break
            
            current += timedelta(days=1)
        
        if not news_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(news_list)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        return df
    
    def fetch_newsapi_news(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch news from NewsAPI.
        Free tier: 100 requests/day, max 1 month history
        """
        if not self.newsapi_key:
            return pd.DataFrame()
        
        coin = symbol.split('-')[0]
        query = f"{coin} OR bitcoin OR cryptocurrency" if coin == 'BTC' else f"{coin} OR cryptocurrency"
        
        news_list = []
        current = max(start_date, datetime.now() - timedelta(days=29))  # Free tier limitation
        
        while current <= end_date:
            url = "https://newsapi.org/v2/everything"
            params = {
                'apiKey': self.newsapi_key,
                'q': query,
                'from': current.strftime('%Y-%m-%d'),
                'to': (current + timedelta(days=7)).strftime('%Y-%m-%d'),
                'language': 'en',
                'sortBy': 'relevancy',
                'pageSize': 100
            }
            
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('articles', []):
                        news_list.append({
                            'date': pd.to_datetime(item['publishedAt']),
                            'title': item['title'],
                            'source': 'NewsAPI'
                        })
                time.sleep(1)  # Rate limiting
            except Exception as e:
                print(f"NewsAPI error: {e}")
                break
            
            current += timedelta(days=7)
        
        if not news_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(news_list)
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        return df
    
    def fetch_all_news(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch news from all available sources"""
        dfs = []
        
        if self.cryptopanic_key:
            cp_news = self.fetch_cryptopanic_news(symbol, start_date, end_date)
            if not cp_news.empty:
                dfs.append(cp_news)
        
        if self.newsapi_key:
            na_news = self.fetch_newsapi_news(symbol, start_date, end_date)
            if not na_news.empty:
                dfs.append(na_news)
        
        if not dfs:
            return pd.DataFrame()
        
        df = pd.concat(dfs, ignore_index=True)
        df = df.drop_duplicates(subset=['title']).sort_values('date')
        return df
    
    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment using TextBlob.
        Returns: -1 (negative) to 1 (positive)
        """
        blob = TextBlob(text)
        return blob.sentiment.polarity


def compute_news_sentiment_series(price_df: pd.DataFrame, symbol: str, use_real_news: bool = False) -> pd.Series:
    """
    Compute daily sentiment scores from news.
    If use_real_news=False or no API keys, falls back to momentum-based simulation.
    """
    client = NewsAPIClient()
    
    if use_real_news and (client.cryptopanic_key or client.newsapi_key):
        start = price_df.index[0].to_pydatetime()
        end = price_df.index[-1].to_pydatetime()
        
        print(f"Fetching real news for {symbol} from {start.date()} to {end.date()}...")
        news_df = client.fetch_all_news(symbol, start, end)
        
        if news_df.empty:
            print("No news fetched, falling back to simulated sentiment")
            return _simulate_sentiment_fallback(price_df)
        
        print(f"Fetched {len(news_df)} news articles, computing sentiment...")
        
        # Compute sentiment per article
        news_df['sentiment'] = news_df['title'].apply(client.analyze_sentiment)
        
        # Aggregate daily sentiment (weighted average)
        news_df['date_only'] = news_df['date'].dt.date
        daily_sentiment = news_df.groupby('date_only')['sentiment'].mean()
        
        # Merge with price data
        sentiment_series = pd.Series(index=price_df.index, dtype=float)
        for date in price_df.index:
            date_key = date.date()
            if date_key in daily_sentiment.index:
                sentiment_series.loc[date] = daily_sentiment.loc[date_key]
            else:
                # Forward fill from previous day or use neutral
                sentiment_series.loc[date] = sentiment_series.iloc[sentiment_series.index.get_loc(date) - 1] if date != price_df.index[0] else 0.0
        
        sentiment_series = sentiment_series.fillna(method='ffill').fillna(0.0)
        return sentiment_series
    else:
        if use_real_news:
            print("No API keys found. Set CRYPTOPANIC_API_KEY or NEWSAPI_API_KEY environment variables.")
            print("Falling back to simulated sentiment based on price momentum.")
        return _simulate_sentiment_fallback(price_df)


def _simulate_sentiment_fallback(price_df: pd.DataFrame) -> pd.Series:
    """Fallback: simulate sentiment from price momentum"""
    import random
    returns = price_df['Adj_Close'].pct_change(7)
    sentiment = returns.clip(-0.15, 0.15) / 0.15
    noise = pd.Series([random.gauss(0, 0.2) for _ in range(len(price_df))], index=price_df.index)
    sentiment = (sentiment + noise).clip(-1, 1)
    return sentiment
