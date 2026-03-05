import requests
import os
import json
from datetime import datetime, timedelta

class SentimentEngine:
    """
    Low-frequency sentiment analysis via Grok API.
    Designed to boost high-probability signals with global context.
    """
    def __init__(self, config):
        self.config = config
        self.api_key = os.getenv("GROK_API_KEY")
        self.base_url = "https://api.x.ai/v1/chat/completions" # Example Grok endpoint
        self.cache = {}
        self.cache_duration = timedelta(hours=4) # Cache sentiment for 4 hours
        self.last_call_time = datetime.min
        self.max_calls_per_day = 5
        self.calls_today = 0
        self.last_reset_date = datetime.now().date()

    def get_sentiment_boost(self, symbol):
        """
        Queries Grok for sentiment on a specific symbol.
        Returns +1 for Bullish, -1 for Bearish, 0 for Neutral/Error.
        """
        if not self.api_key or not self.config.get('grok_enabled', False):
            return 0

        # Reset daily counter
        if datetime.now().date() > self.last_reset_date:
            self.calls_today = 0
            self.last_reset_date = datetime.now().date()

        # Check cache
        if symbol in self.cache:
            data, timestamp = self.cache[symbol]
            if datetime.now() - timestamp < self.cache_duration:
                return data

        # Check rate limits
        if self.calls_today >= self.max_calls_per_day:
            return 0
        
        # Debounce: min 1 hour between calls
        if datetime.now() - self.last_call_time < timedelta(hours=1):
            return 0

        try:
            prompt = f"Analyze the current market sentiment for {symbol} for institutional intraday trading. Provide only one word: BULLISH, BEARISH, or NEUTRAL."
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "grok-1",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }

            response = requests.post(self.base_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                sentiment_text = result['choices'][0]['message']['content'].upper()
                
                boost = 0
                if 'BULLISH' in sentiment_text: boost = 1
                elif 'BEARISH' in sentiment_text: boost = -1
                
                self.cache[symbol] = (boost, datetime.now())
                self.last_call_time = datetime.now()
                self.calls_today += 1
                return boost
            else:
                return 0
        except Exception:
            return 0
