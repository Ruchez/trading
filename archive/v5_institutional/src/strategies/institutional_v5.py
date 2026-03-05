import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from src.strategies.base_strategy import BaseStrategy
from src.utils.market_math import (
    calculate_vwap, detect_bollinger_squeeze, detect_liquidity_sweep,
    calculate_rsi, calculate_adx, calculate_keltner_channels,
    calculate_fibonacci_levels, is_volume_spike, has_rejection_wick,
    calculate_atr
)

class InstitutionalStrategyV5(BaseStrategy):
    """
    Institutional Strategy V5 - "Quality Over Quantity"
    Evolutionary Suite with Multi-TF confluence and scoring.
    """
    def __init__(self, symbol, config):
        super().__init__(symbol, config)
        self.name = "INSTITUTIONAL_V5"
        self.min_confluence_score = 3
        # Symbol-specific configuration
        self.symbol_cfg = config['symbols'].get(symbol, {})

    def check_signal(self, mtf_data, sentiment_boost=0, regime='NEUTRAL'):
        """
        Processes multi-TF data to generate high-probability signals.
        """
        h4  = mtf_data.get('H4', pd.DataFrame())
        h1  = mtf_data.get('H1', pd.DataFrame())
        m15 = mtf_data.get('M15', pd.DataFrame())
        m5  = mtf_data.get('M5', pd.DataFrame())

        if h4.empty or h1.empty or m15.empty or m5.empty:
            return None, None

        # 1. H4 / H1 BIAS (Hard Filter)
        h4_ema50 = h4['close'].ewm(span=50).mean().iloc[-1]
        h4_ema200 = h4['close'].ewm(span=200).mean().iloc[-1]
        h4_trend = 'BULL' if h4_ema50 > h4_ema200 else 'BEAR'

        h1_ema50 = h1['close'].ewm(span=50).mean().iloc[-1]
        h1_trend = 'BULL' if h1_ema50 > h4_ema50 else 'BEAR' # Aligned with H4

        # Bias must be unanimous for trend strategies
        global_bias = h4_trend if h4_trend == h1_trend else 'MIXED'

        signals = []
        
        # 2. SUB-STRATEGY SCANNING WITH CONFLUENCE SCORING
        
        # --- Strategy 1: EMA Pullback (Trend Continuation) ---
        if global_bias != 'MIXED' and regime == 'TRENDING':
            score = 1 # Base score for trend alignment
            reasoning = [f"H4/H1 Aligned {global_bias}"]
            
            # M15 Pullback to EMA20
            m15_ema20 = m15['close'].ewm(span=20).mean().iloc[-1]
            pullback = (global_bias == 'BULL' and m15['low'].iloc[-1] <= m15_ema20) or \
                       (global_bias == 'BEAR' and m15['high'].iloc[-1] >= m15_ema20)
            
            if pullback:
                score += 1
                reasoning.append("M15 EMA20 Pullback")
                
                # Fibonacci Confluence
                fibs = calculate_fibonacci_levels(m15, lookback=50)
                in_fib_zone = (global_bias == 'BULL' and m15['close'].iloc[-1] >= fibs['0.618']) or \
                              (global_bias == 'BEAR' and m15['close'].iloc[-1] <= fibs['0.382'])
                if in_fib_zone:
                    score += 1
                    reasoning.append("Fibonacci Zone Confluence")
                
                # M5 Candle Confirmation
                if has_rejection_wick(m5, 'BUY' if global_bias == 'BULL' else 'SELL', 0.4):
                    score += 1
                    reasoning.append("M5 Rejection Wick")
                    
                # Sentiment Boost
                if (global_bias == 'BULL' and sentiment_boost > 0) or (global_bias == 'BEAR' and sentiment_boost < 0):
                    score += 1
                    reasoning.append("Grok Sentiment Alignment")

                if score >= self.min_confluence_score:
                    return global_bias, f"{score}pt Confluence: " + " | ".join(reasoning)
                else:
                    signals.append((score, global_bias, " | ".join(reasoning)))

        # --- Strategy 2: Liquidity Sweep (High Conviction Reversal) ---
        sweep = detect_liquidity_sweep(m15, window=30)
        if sweep and regime in ['TRENDING', 'VOLATILE']:
            score = 2 # Higher base score for sweeps
            reasoning = ["Liquidity Sweep Detected"]
            
            # Displacement candle confirmation
            last_body = abs(m15['close'].iloc[-1] - m15['open'].iloc[-1])
            avg_body = abs(m15['close'] - m15['open']).iloc[-20:-1].mean()
            if last_body > avg_body * 1.5:
                score += 1
                reasoning.append("Displacement Candle")
                
            # Volume Spike
            if is_volume_spike(m15):
                score += 1
                reasoning.append("Volume Spike")

            if score >= self.min_confluence_score:
                sig = 'BUY' if 'BULLISH' in sweep else 'SELL'
                return sig, f"{score}pt Confluence: " + " | ".join(reasoning)
            else:
                sig = 'BUY' if 'BULLISH' in sweep else 'SELL'
                signals.append((score, sig, " | ".join(reasoning)))

        # --- Strategy 3: VWAP Reversion (Mean Reversion) ---
        if regime == 'RANGING':
            vwap = calculate_vwap(m15).iloc[-1]
            std = m15['close'].rolling(20).std().iloc[-1]
            upper_3 = vwap + (3.0 * std)
            lower_3 = vwap - (3.0 * std)
            
            price = m5['close'].iloc[-1]
            if price > upper_3 or price < lower_3:
                score = 2
                reasoning = ["VWAP 3-Sigma Overextension"]
                
                rsi = calculate_rsi(m15)
                if (price > upper_3 and rsi > 70) or (price < lower_3 and rsi < 30):
                    score += 1
                    reasoning.append(f"RSI Extreme ({rsi:.1f})")
                
                if score >= self.min_confluence_score:
                    sig = 'SELL' if price > upper_3 else 'BUY'
                    return sig, f"{score}pt Confluence: " + " | ".join(reasoning)
                else:
                    sig = 'SELL' if price > upper_3 else 'BUY'
                    signals.append((score, sig, " | ".join(reasoning)))

        # If no signal met threshold, return the best partial match for logging
        if signals:
            best_sig = max(signals, key=lambda x: x[0])
            return None, f"Score {best_sig[0]}/{self.min_confluence_score} ({best_sig[2]})"

        return None, "No Signal (No valid setups found)"

    def check_exit(self, position, mtf_data):
        """Exit logic is mostly handled by TradeManager in V5"""
        return None
