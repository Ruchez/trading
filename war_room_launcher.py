import time
import os
import json
import MetaTrader5 as mt5
from src.main_loop import run_trading_cycle, print_status_pulse, load_config, bridge, trade_manager, regime_engine, sentiment_engine, notifier, commander
import src.main_loop as main_loop

def war_room_init():
    """
    Overrides configuration for the high-intensity War Room session.
    """
    config = load_config()
    
    # 1. Strategy Overrides
    config['mode'] = 'WAR_ROOM'
    config['v5_settings'] = {
        'focused_symbols': ['XAUUSD.m'] # Gold Specialist
    }
    
    # 2. News/Sentiment Scanning override
    # We want a very fast heartbeat for Gold tonight
    print("🚨 [WAR ROOM] Initializing Gold Specialist Engine...")
    print("🛡️  Sentiment Filter: Enabled (Iran/US Geopolitical Hub)")
    print("📈  Trailing: 0.5x ATR (Parabolic Lock-in)")
    
    return config

def main():
    # Setup global instances in main_loop
    main_loop.config = war_room_init()
    
    from src.bridge.mt5_interface import MT5Bridge
    from src.core.trade_manager import TradeManager
    from src.utils.regime_engine import RegimeEngine
    from src.utils.sentiment_engine import SentimentEngine
    from src.comms.command_service import TelegramCommander
    
    main_loop.bridge = MT5Bridge(main_loop.config)
    
    terminal_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal_path):
        print(f"❌ [CRITICAL] Failed to initialize MT5")
        return
    
    main_loop.trade_manager = TradeManager(main_loop.config, main_loop.bridge, main_loop.notifier)
    main_loop.regime_engine = RegimeEngine(main_loop.config)
    main_loop.sentiment_engine = SentimentEngine(main_loop.config)
    
    # Use master account for commander
    accounts = main_loop.load_accounts()
    master_login = str(accounts[0]['login']) if accounts else "MASTER"
    main_loop.commander = TelegramCommander(main_loop.bridge, main_loop.get_risk_engine(master_login), main_loop.notifier)

    print("==================================================")
    print("☢️  WAR ROOM ACTIVE - MONITORING MARKET OPEN...")
    print("==================================================")

    while True:
        try:
            run_trading_cycle()
            print_status_pulse()
            # Fast heartbeat for volatile open
            time.sleep(0.5) 
        except Exception as e:
            print(f"⚠️ [WAR ROOM] Cycle Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
