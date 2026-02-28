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

def calculate_vwap(df):
    """
    Calculates Volume Weighted Average Price (VWAP) for the day.
    """
    # Assuming the df starts from the beginning of the local trading day
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    tp_v = typical_price * df['tick_volume']
    cum_tp_v = tp_v.cumsum()
    cum_v = df['tick_volume'].cumsum()
    return cum_tp_v / cum_v

def detect_bollinger_squeeze(df, window=20, threshold=0.1):
    """
    Detects if the Bollinger Bands are in a 'Squeeze'.
    Threshold is a percentage of the typical price.
    """
    ma = df['close'].rolling(window=window).mean()
    std = df['close'].rolling(window=window).std()
    upper = ma + (2 * std)
    lower = ma - (2 * std)
    bandwidth = (upper - lower) / ma
    
    is_squeezing = bandwidth.iloc[-1] < threshold
    return is_squeezing, upper.iloc[-1], lower.iloc[-1]


def calculate_rsi(df, period=14):
    """
    Calculates RSI (Relative Strength Index).
    Returns the latest RSI value as a float.
    """
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float('nan'))
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def calculate_adx(df, period=14):
    """
    Calculates ADX (Average Directional Index) and +DI/-DI.
    Returns (adx, plus_di, minus_di) as floats.
    """
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm[plus_dm < minus_dm] = 0
    minus_dm[minus_dm < plus_dm] = 0

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr_s = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_s)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_s)

    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=period).mean()
    return adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]


def calculate_keltner_channels(df, period=20, atr_mult=1.5):
    """
    Calculates Keltner Channels.
    Returns (upper, middle, lower) as floats.
    """
    middle = df['close'].ewm(span=period).mean()
    atr = calculate_atr(df, period)
    upper = middle + (atr * atr_mult)
    lower = middle - (atr * atr_mult)
    return upper.iloc[-1], middle.iloc[-1], lower.iloc[-1]


def calculate_fibonacci_levels(df, lookback=50):
    """
    Calculates Fibonacci retracement levels of the last major impulse.
    Returns dict with levels: {'high': H, 'low': L, '0.382': ..., '0.5': ..., '0.618': ...}
    """
    window = df.iloc[-lookback:]
    swing_high = window['high'].max()
    swing_low = window['low'].min()
    diff = swing_high - swing_low
    return {
        'high': swing_high,
        'low': swing_low,
        '0.236': swing_high - diff * 0.236,
        '0.382': swing_high - diff * 0.382,
        '0.500': swing_high - diff * 0.500,
        '0.618': swing_high - diff * 0.618,
        '0.786': swing_high - diff * 0.786,
    }


def is_volume_spike(df, multiplier=1.5, window=20):
    """
    Detects if the latest bar has a volume spike vs recent average.
    Returns True if current volume > multiplier * rolling average.
    """
    avg_vol = df['tick_volume'].iloc[-window-1:-1].mean()
    curr_vol = df['tick_volume'].iloc[-1]
    return curr_vol > (avg_vol * multiplier)


def has_rejection_wick(df, direction='BUY', wick_ratio=0.5):
    """
    Detects a rejection wick on the last candle.
    - BUY rejection: long lower wick (buyers rejected selling pressure)
    - SELL rejection: long upper wick (sellers rejected buying pressure)
    Returns True if wick is significant.
    """
    candle = df.iloc[-1]
    body = abs(candle['close'] - candle['open'])
    total_range = candle['high'] - candle['low']
    if total_range == 0:
        return False
    if direction == 'BUY':
        lower_wick = min(candle['open'], candle['close']) - candle['low']
        return lower_wick >= (total_range * wick_ratio)
    else:
        upper_wick = candle['high'] - max(candle['open'], candle['close'])
        return upper_wick >= (total_range * wick_ratio)
