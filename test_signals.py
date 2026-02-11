import time
from execution.mt5_bridge import MT5Bridge
from ai_brain import AIBrain
from telegram_notifer import TelegramNotifier
from strategies.gold_strategy import GoldInstitutionalStrategy
import json
from market_snapshot import MarketSnapshot

def dry_run_test():
    print("--- Starting Integration Dry Run (Safe Mode) ---")
    
    # 1. Initialize Components
    with open('config.json', 'r') as f:
        config = json.load(f)
        
    bridge = MT5Bridge(config)
    brain = AIBrain()
    notifier = TelegramNotifier()
    
    if not bridge.connect():
        print("[FAIL] Could not connect to MT5.")
        return

    # 2. Test One Symbol (XAUUSD)
    symbol = "XAUUSD"
    print(f"Fetching data for {symbol}...")
    
    mtf_data = bridge.get_mtf_data(symbol)
    if mtf_data['M1'].empty:
        print(f"[FAIL] Could not fetch data for {symbol}.")
        return
        
    print(f"Successfully fetched {len(mtf_data['M1'])} bars of M1 data.")

    # 3. Simulate Strategy Logic
    strategy = GoldInstitutionalStrategy(symbol, config)
    regime = strategy.regime_engine.classify(mtf_data['M1'])
    snapshot = MarketSnapshot.get_narrative(symbol, mtf_data['M1'], mtf_data['H4'], regime)
    
    print("\n--- Consulting Grok AI ---")
    # We use a forced test signal if none exists
    signal = strategy.check_signal(mtf_data['M1']) or "TEST_SIGNAL (BUY)"
    
    print(f"Technical Context: {signal}")
    thought_data = brain.analyze_setup(snapshot, mode="INTRADAY")
    
    print(f"\nAI Analysis Results:")
    print(f"Action: {thought_data.get('action')}")
    print(f"Conviction: {thought_data.get('conviction_score')}%")
    print(f"Reasoning: {thought_data.get('reasoning')}")

    # 4. Test Notification
    print("\n--- Testing Telegram Notification ---")
    if notifier.active:
        success = notifier.send_thought(symbol, thought_data.get('reasoning'), thought_data.get('conviction_score'))
        if success:
            print("[SUCCESS] Notification sent to your phone!")
        else:
            print("[FAIL] Notification failed. Check your Token and Chat ID.")
    else:
        print("[SKIP] Telegram not active in .env.")

    print("\n--- Dry Run Complete! ---")
    print("If you received the notification and are happy with the reasoning, you are ready to run 'python main.py'.")
    
    bridge.disconnect()

if __name__ == "__main__":
    dry_run_test()
