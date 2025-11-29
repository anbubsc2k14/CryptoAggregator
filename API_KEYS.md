# API Key Setup

This project supports fetching real cryptocurrency news for sentiment analysis.

## Supported News APIs

### 1. CryptoCompare (FREE - No Key Required!)
- **Free tier**: 100,000 requests/month - NO API KEY NEEDED for news!
- **Coverage**: Crypto-specific news aggregator
- **Docs**: https://min-api.cryptocompare.com/
- **Setup**: Works automatically! No configuration needed.
- **Optional**: Get API key for higher limits at https://www.cryptocompare.com/cryptopian/api-keys

### 2. CoinMarketCap (Recommended - Best Free Tier)
- **Free tier**: 10,000 requests/month (333/day) 
- **Coverage**: Top crypto news and updates
- **Sign up**: https://coinmarketcap.com/api/
- **Setup**: 
  ```bash
  export COINMARKETCAP_API_KEY='your_key_here'
  ```

### 3. CryptoPanic (Limited Free Tier)
- **Free tier**: 100 requests/day
- **Coverage**: Crypto-specific news aggregator
- **Sign up**: https://cryptopanic.com/developers/api/
- **Setup**: 
  ```bash
  export CRYPTOPANIC_API_KEY='your_cryptopanic_key_here'
  ```

### 4. NewsAPI (General News)
- **Free tier**: 100 requests/day, last 30 days only
- **Coverage**: General news including crypto
- **Sign up**: https://newsapi.org/
- **Setup**:
  ```bash
  export NEWSAPI_API_KEY='your_newsapi_key_here'
  ```

## How to Use

1. **Get API keys** from the providers above
  - **CryptoCompare**: Works immediately, no key needed!
  - **CoinMarketCap**: Best free tier (10K/month)
  - Others: Optional for additional sources

2. **Set environment variables**:
   ```bash
   # Linux/Mac
    export COINMARKETCAP_API_KEY='your_key'
    export CRYPTOCOMPARE_API_KEY='your_key'  # Optional
   export CRYPTOPANIC_API_KEY='your_key'
   export NEWSAPI_API_KEY='your_key'
   
   # Or add to ~/.bashrc or ~/.zshrc for persistence
    echo 'export COINMARKETCAP_API_KEY="your_key"' >> ~/.bashrc
   echo 'export CRYPTOPANIC_API_KEY="your_key"' >> ~/.bashrc
   echo 'export NEWSAPI_API_KEY="your_key"' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Run the dashboard**:
   ```bash
   source .venv/bin/activate
   streamlit run app.py
   ```

4. **Enable real news** in the UI by checking "Use real news APIs"

## Fallback Behavior

If no API keys are configured, the system automatically falls back to simulating sentiment from price momentum. This allows the system to work without API keys for testing purposes.

## Rate Limits

- **CryptoCompare**: 100,000/month (FREE, no key)
- **CoinMarketCap**: 10,000/month (333/day)
- **CryptoPanic**: 100/day (limited)
- NewsAPI: 100 requests/day (free tier)

The news client implements:
- Local caching to minimize API calls
- Rate limiting (1 second between requests)
- Graceful fallback on errors

## News Sentiment Strategy

The sentiment score ranges from -1 (very negative) to +1 (very positive):
- **Sentiment > 0.3**: Aggressive buy
- **0 ≤ Sentiment ≤ 0.3**: Normal buy
- **-0.3 ≤ Sentiment < 0**: Hold (no action)
- **Sentiment < -0.3**: Sell 20% of holdings

Sentiment is computed using TextBlob's polarity analysis on news headlines.
