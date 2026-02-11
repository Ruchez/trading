import pandas as pd
import numpy as np

def calculate_atr(df, period=14):
    """
    Calculates the Average True Range (ATR).
    """
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1]

def detect_fvg(df):
    """
    Identifies Fair Value Gaps (FVG).
    A bullish FVG: low of candle 3 > high of candle 1.
    A bearish FVG: high of candle 3 < low of candle 1.
    """
    fvg = []
    for i in range(2, len(df)):
        # Bullish FVG
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            fvg.append({'index': i-1, 'type': 'BULLISH', 'top': df['low'].iloc[i], 'bottom': df['high'].iloc[i-2]})
        # Bearish FVG
        elif df['high'].iloc[i] < df['low'].iloc[i-2]:
            fvg.append({'index': i-1, 'type': 'BEARISH', 'top': df['low'].iloc[i-2], 'bottom': df['high'].iloc[i]})
    return fvg

def detect_liquidity_sweep(df, window=20):
    """
    Detects liquidity sweeps (stop runs).
    Price dips below a previous low then closes back above it (bullish sweep).
    Price spikes above a previous high then closes back below it (bearish sweep).
    """
    last_low = df['low'].iloc[-window-1:-1].min()
    last_high = df['high'].iloc[-window-1:-1].max()
    
    current_low = df['low'].iloc[-1]
    current_high = df['high'].iloc[-1]
    current_close = df['close'].iloc[-1]

    if current_low < last_low and current_close > last_low:
        return 'BULLISH_SWEEP'
    elif current_high > last_high and current_close < last_high:
        return 'BEARISH_SWEEP'
    return None

def calculate_zscore(series, window=50):
    mean = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    return (series - mean) / std
