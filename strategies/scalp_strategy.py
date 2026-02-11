import MetaTrader5 as mt5
import pandas as pd
from strategies.base_strategy import BaseStrategy
from regime_engine import RegimeEngine

class ScalpStrategy(BaseStrategy):
    """
    Scalping Strategy for fast trades (M1/M5).
    Focuses on quick breakouts or mean reversion.
    """
    def __init__(self, symbol, config, timeframe=mt5.TIMEFRAME_M1):
        super().__init__(symbol, config)
        self.timeframe = timeframe
        self.lookback = 20
        self.regime_engine = RegimeEngine(config)

    def check_signal(self, data):
        """
        Simple M1 Scalping Logic:
        Buy if price breaks above recent high + RSI > 60.
        Sell if price breaks below recent low + RSI < 40.
        """
        if len(data) < self.lookback:
            return None

        current_close = data['close'].iloc[-1]
        previous_high = data['high'].iloc[-21:-1].max()
        previous_low = data['low'].iloc[-21:-1].min()
        
        # Simple RSI calculation (can be replaced with TA-Lib for performance)
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        if current_close > previous_high and current_rsi > 60:
            return 'BUY'
        elif current_close < previous_low and current_rsi < 40:
            return 'SELL'
        
        return None

    def check_exit(self, position, data):
        """
        Exit logic for scalping:
        Scalping usually uses fixed TP/SL set at entry, 
        but we can add a trailing stop or reversal logic here.
        """
        # For this example, we let the fixed TP/SL in MT5 handle it
        # but could implement a time-based exit (e.g. close after 5 mins)
        return False
