import os
import json
import MetaTrader5 as mt5
from src.bridge.mt5_interface import MT5Bridge
from src.utils.backtester_v5 import BacktesterV5

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'settings.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ CONFIG ERROR: {e}")
        return {}

def get_user_choice():
    print("\n" + "="*40)
    print("      🏛️  V5 BACKTEST INTERFACE  🏛️")
    print("="*40)
    print("Choose your backtest period:")
    print("1. 30 Days (Quick Logic Check)")
    print("2. 3 Months (Quarterly Cycle)")
    print("3. 6 Months (Semi-Annual)")
    print("4. 1 Year (Standard Benchmark)")
    print("5. 3 Years (Institutional Grade)")
    print("6. 5 Years (Macro Depth)")
    print("7. Custom (Enter days manually)")
    print("-" * 40)
    
    choice = input("Enter choice (1-7): ").strip()
    
    if choice == '1': return 30
    elif choice == '2': return 90
    elif choice == '3': return 180
    elif choice == '4': return 365
    elif choice == '5': return 1095
    elif choice == '6': return 1825
    elif choice == '7':
        try:
            days = int(input("Enter number of days: ").strip())
            return days
        except:
            print("⚠️ Invalid input. Defaulting to 1 Year.")
            return 365
    else:
        print("⚠️ Invalid choice. Defaulting to 1 Year.")
        return 365

def main():
    config = load_config()
    bridge = MT5Bridge(config)
    
    # 1. Connect (Sync)
    if not bridge.connect():
        print("❌ Could not connect to MT5 for data retrieval.")
        return

    # 2. Get Real Equity
    acc_info = mt5.account_info()
    if not acc_info:
        print("❌ Could not retrieve account info.")
        return
        
    real_equity = acc_info.equity
    print(f"✅ Real Equity Synchronized: ${real_equity:,.2f}")

    # 3. Get Timeframe Choice
    days_to_test = get_user_choice()

    # 4. Initialize Backtester with Real Equity
    backtester = BacktesterV5(bridge, config, initial_balance=real_equity)
    
    # Symbols from settings or default set
    symbols = config.get('v5_settings', {}).get('focused_symbols', ["XAUUSD.m", "BTCUSD.m", "EURUSD.m"])
    
    all_results = {}
    for symbol in symbols:
        results = backtester.run(symbol, days=days_to_test)
        if results:
            all_results[symbol] = results

    print("\n" + "="*40)
    print("✅ All Backtests Completed.")
    print("="*40)
    
    # Keep terminal open if needed (optional)
    # input("\nPress Enter to exit...")
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Backtest aborted by user.")
    except Exception as e:
        print(f"❌ CRITICAL BACKTEST ERROR: {e}")
        import traceback
        traceback.print_exc()
