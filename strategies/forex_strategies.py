from strategies.base_strategy import BaseStrategy
from regime_engine import RegimeEngine
from indicators import detect_fvg
import MetaTrader5 as mt5
from datetime import datetime

class LondonBreakoutStrategy(BaseStrategy):
    """
    GBPUSD: London Open Breakout Strategy.
    Targets the volatility spike during the London session open (8 AM - 10 AM London time).
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.regime_engine = RegimeEngine(config)

    def check_signal(self, data):
        # 1. Time Check: Only trade London Open (Approx 7:00 - 10:00 UTC)
        # Note: In production, use a more robust timezone handling library
        now_hour = datetime.utcnow().hour
        if now_hour < 7 or now_hour > 10:
            return None

        # 2. Daily Bias Check (D1 > 200 EMA)
        regime = self.regime_engine.classify(data)
        if regime['trend'] == "NEUTRAL":
            return None

        # 3. Breakout Logic: Price breaks the Asian Range High/Low
        # Mocking Asian range (00:00 - 07:00 UTC)
        asian_range = data.iloc[-30:-1] # Simplified proxy for late Asia session
        asian_high = asian_range['high'].max()
        asian_low = asian_range['low'].min()
        
        current_price = data['close'].iloc[-1]
        
        if current_price > asian_high and regime['trend'] == "BULLISH":
            return 'BUY'
        elif current_price < asian_low and regime['trend'] == "BEARISH":
            return 'SELL'
            
        return None

    def check_exit(self, position, data):
        return False # Let SL/TP handle it or add time-based exit (EO-London)

class CarryTrendStrategy(BaseStrategy):
    """
    USDJPY: Carry Trend Strategy.
    Follows interest rate differentials and pulls back to the 50 EMA in established trends.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.regime_engine = RegimeEngine(config)

    def check_signal(self, data):
        regime = self.regime_engine.classify(data)
        
        # Only trade during clear trends
        if regime['trend'] == "NEUTRAL":
            return None

        current_price = data['close'].iloc[-1]
        ema50 = regime['ema50']
        
        # Distance to EMA filter (Enter on Pullback)
        distance = abs(current_price - ema50) / ema50
        
        if regime['trend'] == "BULLISH" and current_price > ema50 and distance < 0.002:
            return 'BUY'
        elif regime['trend'] == "BEARISH" and current_price < ema50 and distance < 0.002:
            return 'SELL'

        return None

    def check_exit(self, position, data):
        return False

class GBPJPYVolatilityStrategy(BaseStrategy):
    """
    GBPJPY: Volatility Expansion Strategy ("The Beast").
    Focuses on early London volatility spikes and trend alignment.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.regime_engine = RegimeEngine(config)

    def check_signal(self, data):
        # 1. Time Check: London Session Focus (07:00 - 12:00 UTC)
        now_hour = datetime.utcnow().hour
        if now_hour < 7 or now_hour > 12:
            return None

        # 2. Volatility Check: High ATR Spike
        # Calculating ATR manually since TA-Lib might not be present
        high_low = data['high'] - data['low']
        atr = high_low.rolling(window=14).mean().iloc[-1]
        vol = high_low.iloc[-1]
        
        if vol < 1.3 * atr: # Requires a 30% spike in current candle volatility
            return None

        # 3. Trend Alignment
        regime = self.regime_engine.classify(data)
        current_price = data['close'].iloc[-1]
        
        if regime['trend'] == "BULLISH" and current_price > data['high'].iloc[-2]:
            return 'BUY'
        elif regime['trend'] == "BEARISH" and current_price < data['low'].iloc[-2]:
            return 'SELL'

        return None

    def check_exit(self, position, data):
        return False
