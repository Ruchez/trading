import numpy as np
import pandas as pd

class RegimeEngine:
    """
    Classifies the market into different regimes based on volatility and trend.
    """
    def __init__(self, config):
        self.config = config

    def classify(self, df):
        """
        Input: DataFrame with OHLC data.
        Returns: Dict with trend and volatility classification.
        """
        if len(df) < 50:
            return {"trend": "NEUTRAL", "volatility": "LOW"}

        # 1. Trend Classification (using EMA 50 and 200)
        ema50 = df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
        current_price = df['close'].iloc[-1]

        trend = "NEUTRAL"
        if current_price > ema50 > ema200:
            trend = "BULLISH"
        elif current_price < ema50 < ema200:
            trend = "BEARISH"

        # 2. Volatility Classification (ATR relative to moving average)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        avg_atr = atr.rolling(window=50).mean().iloc[-1]
        current_atr = atr.iloc[-1]

        volatility = "STABLE"
        if current_atr > 1.5 * avg_atr:
            volatility = "EXPANSION"
        elif current_atr < 0.7 * avg_atr:
            volatility = "COMPRESSION"

        return {
            "trend": trend,
            "volatility": volatility,
            "atr": current_atr,
            "ema50": ema50,
            "ema200": ema200
        }
