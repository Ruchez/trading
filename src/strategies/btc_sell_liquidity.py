import MetaTrader5 as mt5
import pandas as pd
from src.strategies.base_strategy import BaseStrategy
from src.utils.market_math import (
    detect_liquidity_sweep, is_volume_spike, has_rejection_wick,
    calculate_atr
)

class BTCSellLiquidityStrategy(BaseStrategy):
    """
    Specialized Bitcoin Strategy: ONLY SELLS.
    Confluence from H4 and M15 Liquidity Sweeps of Highs.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.name = "BTC_LIQUIDITY_SELL"

    def check_signal(self, mtf_data, sentiment_boost=0, regime='NEUTRAL'):
        """
        Targeting liquidity sweeps (spikes above previous highs) on H4 and M15.
        ONLY returns 'SELL' signals.
        """
        h4  = mtf_data.get('H4', pd.DataFrame())
        m15 = mtf_data.get('M15', pd.DataFrame())
        m5  = mtf_data.get('M5', pd.DataFrame())

        if h4.empty or m15.empty or m5.empty:
            return None, None

        # 1. Primary Filter: H4 Liquidity Condition
        # - Either a fresh H4 bearish sweep of a swing high
        # - Or H4 price is currently testing the H4 high with rejection
        h4_sweep = detect_liquidity_sweep(h4, window=12) # Check last 12 bars (~2 days)
        h4_high_level = h4['high'].iloc[-24:-1].max()
        price_at_h4_high = h4['high'].iloc[-1] >= (h4_high_level * 0.9998)
        h4_bearish_confluence = (h4_sweep == 'BEARISH_SWEEP') or price_at_h4_high
        
        if not h4_bearish_confluence:
            return None, "Wait (No H4 Liquidity Zone)"

        # 2. Secondary Filter: M15 Liquidity Sweep (Timing)
        m15_sweep = detect_liquidity_sweep(m15, window=40)
        
        score = 2
        reasoning = ["H4 Liquidity Zone"]
        
        if m15_sweep == 'BEARISH_SWEEP':
            score += 1
            reasoning.append("M15 Bearish Liquidity Sweep")
            
            # 3. M5 Confirmation: Rejection Wick
            if has_rejection_wick(m5, 'SELL', 0.4):
                score += 1
                reasoning.append("M5 Upper Wick Rejection")

            # 4. Sentiment (Negative Sentiment aligns with Sells)
            if sentiment_boost < 0:
                score += 1
                reasoning.append("Negative Grok Sentiment Alignment")

            # Final check - ONLY SELLS allowed
            return 'SELL', f"{score}pt BTC Sell Confluence: " + " | ".join(reasoning)
        
        return None, f"Wait (Score {score}/3 - {reasoning[0]})"

    def check_exit(self, position, mtf_data):
        """Exit handled by TradeManager"""
        return None
