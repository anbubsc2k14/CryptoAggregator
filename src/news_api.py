import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from textblob import TextBlob
from typing import Optional
import time


class NewsAPIClient:
    """Fetch crypto news from multiple sources: CoinMarketCap, CryptoCompare, NewsAPI, CryptoPanic"""
    
    def __init__(self):
        self.coinmarketcap_key = os.getenv('COINMARKETCAP_API_KEY', '')
        self.cryptocompare_key = os.getenv('CRYPTOCOMPARE_API_KEY', '')
        self.newsapi_key = os.getenv('NEWSAPI_API_KEY', '')
        self.cryptopanic_key = os.getenv('CRYPTOPANIC_API_KEY', '')
        self.cache = {}
    
    def fetch_coinmarketcap_news(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch news from CoinMarketCap API.
        Free tier: 10,000 requests/month (333/day)
        Sign up: https://coinmarketcap.com/api/
        """
        # Normalize incoming datetimes to naive (drop tz) for uniform comparisons
        if getattr(start_date, 'tzinfo', None) is not None:
            start_date = start_date.replace(tzinfo=None)
        if getattr(end_date, 'tzinfo', None) is not None:
            end_date = end_date.replace(tzinfo=None)
        if not self.coinmarketcap_key:
            return pd.DataFrame()
    
        coin = symbol.split('-')[0]
        news_list = []
    
        url = "https://pro-api.coinmarketcap.com/v1/content/latest"
        headers = {
            'X-CMC_PRO_API_KEY': self.coinmarketcap_key,
            'Accept': 'application/json'
        }
        params = {
            'symbol': coin,
            'start': 1,
            'limit': 100
        }
    
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('data', []):
                    pub_date = pd.to_datetime(item.get('releaseDate') or item.get('createdDate'), errors='coerce')
                    if pub_date is None or pd.isna(pub_date):
                        continue
                    if getattr(pub_date, 'tzinfo', None) is not None:
                        pub_date = pub_date.tz_localize(None)
                    if start_date <= pub_date <= end_date:
                        news_list.append({
                            'date': pub_date,
                            'title': item.get('title', ''),
                            'body': item.get('subtitle', ''),
                            'source': 'CoinMarketCap'
                        })
        except Exception as e:
            print(f"CoinMarketCap API error: {e}")
    
        return pd.DataFrame(news_list) if news_list else pd.DataFrame()
    
    def fetch_cryptocompare_news(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch news from CryptoCompare API.
        Free tier: 100,000 requests/month (completely free, no key required for news!)
        Docs: https://min-api.cryptocompare.com/
        """
        if getattr(start_date, 'tzinfo', None) is not None:
            start_date = start_date.replace(tzinfo=None)
        if getattr(end_date, 'tzinfo', None) is not None:
            end_date = end_date.replace(tzinfo=None)
        coin = symbol.split('-')[0]
        news_list = []
        
        url = "https://min-api.cryptocompare.com/data/v2/news/"
        params = {
            'categories': coin,
            'lang': 'EN'
        }
        
        if self.cryptocompare_key:
            params['api_key'] = self.cryptocompare_key
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('Data', []):
                    pub_date = pd.to_datetime(item.get('published_on'), unit='s', utc=True).tz_localize(None)
                    if start_date <= pub_date <= end_date:
                        news_list.append({
                            'date': pub_date,
                            'title': item.get('title', ''),
                            'body': item.get('body', ''),
                            'source': 'CryptoCompare'
                        })
        except Exception as e:
            print(f"CryptoCompare API error: {e}")
        
        return pd.DataFrame(news_list) if news_list else pd.DataFrame()
    
    def fetch_cryptopanic_news(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch news from CryptoPanic API.
        Free tier: 100 requests/day
        """
        if getattr(start_date, 'tzinfo', None) is not None:
            start_date = start_date.replace(tzinfo=None)
        if getattr(end_date, 'tzinfo', None) is not None:
            end_date = end_date.replace(tzinfo=None)
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
            
            # Add simple retries with exponential backoff
            for attempt in range(3):
                try:
                    response = requests.get(url, params=params, timeout=20)
                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get('results', []):
                            pub_date = pd.to_datetime(item.get('published_at'), errors='coerce')
                            if pub_date is None or pd.isna(pub_date):
                                continue
                            if getattr(pub_date, 'tzinfo', None) is not None:
                                pub_date = pub_date.tz_localize(None)
                            if start_date <= pub_date <= end_date:
                                news_list.append({
                                    'date': pub_date,
                                    'title': item.get('title', ''),
                                    'body': '',
                                    'source': 'CryptoPanic'
                                })
                        # Cache results for the day
                        self.cache[cache_key] = data.get('results', [])
                        break
                    else:
                        time.sleep(1 * (attempt + 1))
                except Exception as e:
                    if attempt == 2:
                        print(f"CryptoPanic API error: {e}")
                    time.sleep(1 * (attempt + 1))
            
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
        if getattr(start_date, 'tzinfo', None) is not None:
            start_date = start_date.replace(tzinfo=None)
        if getattr(end_date, 'tzinfo', None) is not None:
            end_date = end_date.replace(tzinfo=None)
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
                        pub_date = pd.to_datetime(item['publishedAt'], errors='coerce')
                        if pub_date is None or pd.isna(pub_date):
                            continue
                        if getattr(pub_date, 'tzinfo', None) is not None:
                            pub_date = pub_date.tz_localize(None)
                        news_list.append({
                            'date': pub_date,
                            'title': item['title'],
                            'body': item.get('description', ''),
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
        
        # Try CoinMarketCap first (best free tier)
        if self.coinmarketcap_key:
            cmc_news = self.fetch_coinmarketcap_news(symbol, start_date, end_date)
            if not cmc_news.empty:
                dfs.append(cmc_news)
        
        # CryptoCompare (no key required!)
        cc_news = self.fetch_cryptocompare_news(symbol, start_date, end_date)
        if not cc_news.empty:
            dfs.append(cc_news)
        
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
    
    if use_real_news and (client.coinmarketcap_key or client.cryptocompare_key or client.cryptopanic_key or client.newsapi_key):
        start = price_df.index[0].to_pydatetime()
        end = price_df.index[-1].to_pydatetime()
        if getattr(start, 'tzinfo', None) is not None:
            start = start.replace(tzinfo=None)
        if getattr(end, 'tzinfo', None) is not None:
            end = end.replace(tzinfo=None)
        
        print(f"Fetching real news for {symbol} from {start.date()} to {end.date()}...")
        news_df = client.fetch_all_news(symbol, start, end)
        
        if news_df.empty:
            print("No news fetched, falling back to simulated sentiment")
            return _simulate_sentiment_fallback(price_df)
        
        print(f"Fetched {len(news_df)} news articles, computing sentiment...")
        
        # Compute sentiment per article (combine title + body)
        news_df['text'] = news_df['title'] + ' ' + news_df['body'].fillna('')
        news_df['sentiment'] = news_df['text'].apply(client.analyze_sentiment)
        
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
            print("No API keys found. Set COINMARKETCAP_API_KEY, CRYPTOCOMPARE_API_KEY, CRYPTOPANIC_API_KEY, or NEWSAPI_API_KEY environment variables.")
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
