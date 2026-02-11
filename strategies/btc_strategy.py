from indicators import calculate_zscore
from strategies.base_strategy import BaseStrategy
from regime_engine import RegimeEngine
import pandas as pd

class BTCInstitutionalStrategy(BaseStrategy):
    """
    BTCUSD Strategy: Z-Score Mean Reversion + Momentum Filter.
    Optimized for the post-2025 corrective regime.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.regime_engine = RegimeEngine(config)
        self.window = 50

    def check_signal(self, data):
        if len(data) < self.window:
            return None

        # 1. Calculate Z-Score
        zscores = calculate_zscore(data['close'], window=self.window)
        current_z = zscores.iloc[-1]
        
        # 2. RSI Filter
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # 3. Volume Surge Proxy
        avg_vol = data['tick_volume'].rolling(window=20).mean().iloc[-1]
        current_vol = data['tick_volume'].iloc[-1]
        vol_surge = current_vol > 1.5 * avg_vol

        # Short Entry: Z > +3.0 + RSI > 80 + Vol Fade (or surge at peak)
        if current_z > 3.0 and current_rsi > 80:
            self.latest_indicators = {"zscore": current_z, "rsi": current_rsi, "vol_surge": vol_surge}
            return 'SELL'
            
        # Long Entry: Z < -2.5 + Vol Surge (Capitulation)
        elif current_z < -2.5 and vol_surge:
            self.latest_indicators = {"zscore": current_z, "rsi": current_rsi, "vol_surge": vol_surge}
            return 'BUY'
            
        return None

    def check_exit(self, position, data):
        # Exit on touch of the mean (z-score near 0)
        zscores = calculate_zscore(data['close'], window=self.window)
        current_z = zscores.iloc[-1]
        
        if (position.type == 0 and current_z >= 0) or (position.type == 1 and current_z <= 0):
            return True # Close position
        return False
