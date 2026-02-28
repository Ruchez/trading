import os
import json
import MetaTrader5 as mt5
from src.bridge.mt5_interface import MT5Bridge
from src.utils.backtester_v5 import BacktesterV5
from src.utils.ai_learning_engine import AI_LearningEngine

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
    print("      🏛️  V5 AI LEARNING INTERFACE  🏛️")
    print("="*40)
    print("Choose your simulation depth:")
    print("1. 30 Days (Quick Logic Check)")
    print("2. 3 Months (Quarterly Cycle)")
    print("3. 6 Months (Semi-Annual)")
    print("4. 1 Year (Standard Benchmark)")
    print("5. 3 Years (Institutional Grade)")
    print("6. 5 Years (Macro Depth)")
    print("7. Custom (Enter days manually)")
    print("-" * 40)
    
    choice = input("Enter choice (1-7): ").strip()
    
    mapping = {'1': 30, '2': 90, '3': 180, '4': 365, '5': 1095, '6': 1825}
    if choice in mapping:
        return mapping[choice]
    elif choice == '7':
        try:
            return int(input("Enter number of days: ").strip())
        except:
            return 365
    return 365

def main():
    config = load_config()
    bridge = MT5Bridge(config)
    
    if not bridge.connect():
        print("❌ Could not connect to MT5.")
        return

    acc_info = mt5.account_info()
    if not acc_info:
        print("❌ Could not retrieve account info.")
        return
        
    real_equity = acc_info.equity
    print(f"✅ Real Equity Synchronized: ${real_equity:,.2f}")

    days_to_test = get_user_choice()
    backtester = BacktesterV5(bridge, config, initial_balance=real_equity)
    
    symbols = config.get('v5_settings', {}).get('focused_symbols', ["XAUUSD.m", "BTCUSD.m", "EURUSD.m"])
    
    for symbol in symbols:
        backtester.run(symbol, days=days_to_test)

    print("\n" + "="*40)
    print("✅ All Simulation Steps Completed.")
    print("="*40)
    
    # AI POST-MORTEM OPTION
    choice = input("\n🧠 Would you like to run a Deep AI Post-Mortem on these trades? (y/n): ").strip().lower()
    if choice == 'y':
        learning_engine = AI_LearningEngine(config)
        log_path = os.path.join("logs", "backtest_learning_data.json")
        
        analysis = learning_engine.analyze_trades(log_path)
        
        print("\n" + "="*60)
        print("🏛️  AI STRATEGY POST-MORTEM REPORT  🏛️")
        print("="*60)
        print(analysis)
        print("="*60)
        
        # Save analysis to file
        with open(os.path.join("logs", "ai_strategy_refinement.md"), "w") as f:
            f.write(analysis)
        print(f"\n📄 Report saved to logs/ai_strategy_refinement.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Aborted.")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
