import pandas as pd
import MetaTrader5 as mt5

class MarketSnapshot:
    """
    Prepares a technical narrative of the market state for LLM ingestion.
    """
    @staticmethod
    def get_narrative(symbol, m1_data, h4_data, regime):
        """
        Combines M1 and H4 data into a technical briefing.
        """
        # Calculate some quick stats for the narrative
        curr_price = m1_data['close'].iloc[-1]
        h4_prev = h4_data['close'].iloc[-1]
        h4_trend = "BULLISH" if h4_prev > h4_data['close'].iloc[-20:].mean() else "BEARISH"
        
        # Prepare the indicators string
        indicators = []
        if 'rsi' in m1_data: indicators.append(f"RSI: {m1_data['rsi'].iloc[-1]:.1f}")
        if 'zscore' in m1_data: indicators.append(f"Z-Score: {m1_data['zscore'].iloc[-1]:.1f}")
        
        narrative = f"""
        SYMBOL: {symbol}
        CURRENT PRICE: {curr_price:.5f}
        
        [REGIME]: {regime['trend']} (Volatility: {regime.get('vol_state', 'NORMAL')})
        
        [HIGHER TIMEFRAME (H4)]:
        Last Candle Close: {h4_prev:.5f}
        Trend Structure: {h4_trend}
        
        [LOWER TIMEFRAME (M1)]:
        Recent Momentum: {'Up' if m1_data['close'].iloc[-1] > m1_data['close'].iloc[-5] else 'Down'}
        Key Indicators: {', '.join(indicators)}
        """
        return narrative
