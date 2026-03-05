import pandas as pd
import numpy as np

class RegimeEngine:
    """
    Classifies market state based on volatility and trend strength.
    States: 'TRENDING', 'RANGING', 'VOLATILE'
    """
    def __init__(self, config):
        self.config = config

    def classify(self, data):
        """
        Classifies the current market regime based on OHLC data.
        """
        if len(data) < 20:
            return 'NEUTRAL'
        
        close = data['close']
        
        # 1. Trend Strength (ADX equivalent/Simple logic)
        ema_20 = close.ewm(span=20).mean()
        is_trending = abs(close.iloc[-1] - ema_20.iloc[-1]) > (close.std() * 0.5)
        
        # 2. Volatility (ATR-based)
        high_low = data['high'] - data['low']
        atr = high_low.rolling(14).mean()
        curr_volatility = atr.iloc[-1]
        avg_volatility = atr.mean()
        
        if curr_volatility > avg_volatility * 1.5:
            return 'VOLATILE'
        
        if is_trending:
            return 'TRENDING'
        else:
            return 'RANGING'
