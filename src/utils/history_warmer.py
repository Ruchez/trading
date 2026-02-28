import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime

def warm_history(symbol, timeframes, days=365):
    """
    Forces MT5 to download historical data by requesting it in smaller chunks
    moving backwards in time. This 'warms' the terminal cache.
    """
    print(f"🌡️  Warming history for {symbol}...")
    
    for tf_name, tf in timeframes.items():
        print(f"  [{tf_name}] Pulling data...")
        # Start with 5000 bars and move back
        chunk_size = 5000
        total_bars = 0
        
        # We try to pull in chunks to reach the target (approx)
        # 1 year M5 = 105k bars
        target = days * 24 * 60
        if tf == mt5.TIMEFRAME_M5: target = days * 288
        if tf == mt5.TIMEFRAME_M15: target = days * 96
        if tf == mt5.TIMEFRAME_H1: target = days * 24
        if tf == mt5.TIMEFRAME_H4: target = days * 6
        
        for i in range(0, target, chunk_size):
            rates = mt5.copy_rates_from_pos(symbol, tf, i, chunk_size)
            if rates is None or len(rates) == 0:
                print(f"    Reached broker limit for {tf_name} at index {i}")
                break
            total_bars += len(rates)
            # Short sleep to prevent terminal locking
            time.sleep(0.1)
        
        print(f"  ✅ {tf_name} Ready: ~{total_bars} bars cached.")

if __name__ == "__main__":
    if not mt5.initialize():
        print("MT5 Init Failed")
        exit()
        
    symbols = ["XAUUSD.m", "BTCUSD.m", "EURUSD.m", "USDJPY.m", "AUDUSD.m"]
    tfs = {
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4
    }
    
    for s in symbols:
        warm_history(s, tfs)
    
    mt5.shutdown()
    print("\n🔥 All history warmed and cached. You can now run the backtester.")
