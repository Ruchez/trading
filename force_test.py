import MetaTrader5 as mt5
from execution.mt5_bridge import MT5Bridge
import json
import time
import sys

# Redirect stderr to stdout so we capture tracebacks
sys.stderr = sys.stdout

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def force_test():
    import traceback
    try:
        with open("force_test.log", "w", encoding="utf-8") as f:
            def log(msg):
                print(msg)
                f.write(msg + "\n")
                f.flush()

            log("--- ATR BE LOGIC VERIFICATION ---")
            
            config = load_config()
            bridge = MT5Bridge(config)
            
            if not bridge.connect():
                log("[FAIL] Could not connect to MT5.")
                return

            symbol = "EURUSD.m" # Using EURUSD.m for test
            log(f"Targeting: {symbol}")
            
            # Fetch M1 Data
            log("Fetching M1 Data for ATR Calculation...")
            m1_data = bridge.get_data(symbol, mt5.TIMEFRAME_M1, 20)
            
            if not m1_data.empty and len(m1_data) > 15:
                from indicators import calculate_atr
                current_atr = calculate_atr(m1_data)
                
                log(f"Current ATR (14): {current_atr:.5f}")
                
                # BE Settings
                be_mult = config['risk_management'].get('be_trigger_atr_multiple', 1.5)
                # Note: 'point' is needed for buffer conversion
                symbol_info = mt5.symbol_info(symbol)
                be_buffer_points = config['risk_management'].get('be_buffer_points', 50)
                be_buffer_val = be_buffer_points * symbol_info.point
                
                trigger_dist = current_atr * be_mult
                
                log(f"Config Multiplier: {be_mult}")
                log(f"BE Trigger Distance (Price Delta): {trigger_dist:.5f}")
                log(f"BE Buffer (Value): {be_buffer_val:.5f} ({be_buffer_points} points)")
                
                log(f"EXAMPLE SCENARIO:")
                current_price = 1.08500
                entry_price = 1.08000
                dist = abs(current_price - entry_price)
                log(f"  Entry: {entry_price:.5f}, Current: {current_price:.5f}, Dist: {dist:.5f}")
                
                if dist > trigger_dist:
                     log(f"  Result: TRIGGERED! (Dist {dist:.5f} > Trigger {trigger_dist:.5f})")
                     log(f"  New SL would be: {entry_price + be_buffer_val:.5f}")
                else:
                     log(f"  Result: HOLD. (Dist {dist:.5f} <= Trigger {trigger_dist:.5f})")
            else:
                log("[FAIL] Could not fetch sufficient M1 data.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    force_test()
