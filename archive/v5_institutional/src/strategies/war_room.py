import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from src.strategies.base_strategy import BaseStrategy
from src.utils.market_math import (
    calculate_vwap, calculate_rsi, calculate_atr,
    is_volume_spike, has_rejection_wick
)

class WarRoomGoldStrategy(BaseStrategy):
    """
    War Room Specialist Strategy - "Gold Crisis Alpha"
    Optimized for Geopolitical Volatility, Market Open Gaps, and Parabolic Trends.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.name = "WAR_ROOM_GOLD"
        self.min_confluence_score = 3
        # War Room specific overrides
        self.atr_trail_multiplier = 0.5 # Ultra-tight trailing
        self.max_positions = 3
        self.fixed_lot = 0.01 

    def check_signal(self, mtf_data, sentiment_boost=0, regime='NEUTRAL'):
        """
        Tactical scanning for XAUUSD crisis setups.
        """
        m5  = mtf_data.get('M5', pd.DataFrame())
        m15 = mtf_data.get('M15', pd.DataFrame())
        h1  = mtf_data.get('H1', pd.DataFrame())

        if m15.empty or m5.empty or h1.empty:
            return None, None

        # 1. GEOPOLITICAL SENTIMENT LOCK (Mandatory)
        # We only trade 'BULL' if sentiment is positive for Gold (Conflict/War)
        if sentiment_boost <= 0:
            return None, "Awaiting Bullish Geopolitical Confirmation (Grok/News)"

        score = 0
        reasoning = ["Geopolitical Sentiment Validated"]
        
        # 2. GAP ATTACK LOGIC (Market Open Specialist)
        # If price opens significantly above last Friday's close
        last_close = h1['close'].iloc[-2] # Previous candle
        current_open = h1['open'].iloc[-1]
        gap_percent = ((current_open - last_close) / last_close) * 100
        
        if gap_percent > 0.5: # 0.5% Gap Up is significant for Gold
            score += 2
            reasoning.append(f"Significant Gap Up ({gap_percent:.2f}%)")

        # 3. MOMENTUM CONFLUENCE
        rsi = calculate_rsi(m15)
        if rsi > 60: # Strong bullish momentum
            score += 1
            reasoning.append(f"Strong M15 Momentum (RSI: {rsi:.1f})")

        # 4. TREND ALIGNMENT (EMA Stack)
        ema20 = m15['close'].ewm(span=20).mean().iloc[-1]
        ema50 = m15['close'].ewm(span=50).mean().iloc[-1]
        if m15['close'].iloc[-1] > ema20 > ema50:
            score += 1
            reasoning.append("EMA Trend Stack (M15)")

        # 5. VOLATILITY SURGE
        if is_volume_spike(m15, multiplier=2.0): # Looking for "Crisis Volume"
            score += 1
            reasoning.append("Crisis Volume Surge Detected")

        if score >= self.min_confluence_score:
            return 'BUY', f"WAR ROOM {score}pt: " + " | ".join(reasoning)

        return None, None

    def get_trailing_params(self):
        """Returns War-Room specific trailing config"""
        return {
            'trail_atr': self.atr_trail_multiplier,
            'be_r': 0.8, # Earlier break-even for safety
            'max_pos': self.max_positions,
            'fixed_lot': self.fixed_lot
        }
