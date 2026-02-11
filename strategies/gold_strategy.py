from indicators import detect_fvg, detect_liquidity_sweep
from strategies.base_strategy import BaseStrategy
from regime_engine import RegimeEngine

class GoldInstitutionalStrategy(BaseStrategy):
    """
    High-end XAUUSD strategy: Liquidity Sweep + FVG Trend Continuation.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.regime_engine = RegimeEngine(config)

    def check_signal(self, data):
        regime = self.regime_engine.classify(data)
        
        # We only trade Gold in Bullish Trend or High Vol Expansion
        if regime['trend'] != "BULLISH":
            return None

        # Check for Liquidity Sweep
        sweep = detect_liquidity_sweep(data)
        
        # Check for FVG
        fvgs = detect_fvg(data)
        recent_fvg = fvgs[-1] if fvgs else None

        if sweep == 'BULLISH_SWEEP' and recent_fvg and recent_fvg['type'] == 'BULLISH':
            self.latest_indicators = {
                "sweep": sweep,
                "fvg_type": recent_fvg['type'],
                "ema200": regime['ema200'],
                "adx": regime.get('adx', 0)
            }
            return 'BUY'
            
        return None

    def check_exit(self, position, data):
        # Implement institutional trailing or structure-based exit here
        return False
