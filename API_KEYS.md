# API Key Setup

This project supports fetching real cryptocurrency news for sentiment analysis.

## Supported News APIs

### 1. CryptoPanic (Recommended for crypto)
- **Free tier**: 100 requests/day
- **Coverage**: Crypto-specific news aggregator
- **Sign up**: https://cryptopanic.com/developers/api/
- **Setup**: 
  ```bash
  export CRYPTOPANIC_API_KEY='your_cryptopanic_key_here'
  ```

### 2. NewsAPI
- **Free tier**: 100 requests/day, last 30 days only
- **Coverage**: General news including crypto
- **Sign up**: https://newsapi.org/
- **Setup**:
  ```bash
  export NEWSAPI_API_KEY='your_newsapi_key_here'
  ```

## How to Use

1. **Get API keys** from the providers above (both free)

2. **Set environment variables**:
   ```bash
   # Linux/Mac
   export CRYPTOPANIC_API_KEY='your_key'
   export NEWSAPI_API_KEY='your_key'
   
   # Or add to ~/.bashrc or ~/.zshrc for persistence
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

- CryptoPanic: 100 requests/day (free tier)
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
