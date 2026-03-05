import sys
import os
import time
import json
import MetaTrader5 as mt5
import pandas as pd
import traceback

# Adjusting sys.path to allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bridge.mt5_interface import MT5Bridge
from src.strategies import get_strategy
from src.core.risk_manager import RiskEngine
from src.core.trade_manager import TradeManager
from src.comms.notifier_service import TelegramNotifier
from src.comms.command_service import TelegramCommander
from src.utils.market_math import calculate_atr
from src.utils.regime_engine import RegimeEngine
from src.utils.sentiment_engine import SentimentEngine
from src.utils.trade_db import TradeDB

ACCOUNTS_FILE = os.path.join("config", "accounts.json")

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        return []
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'settings.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ CONFIG ERROR: {e}")
        return {}

# Global instances
config = load_config()
bridge = None
risk_engines = {}
notifier = TelegramNotifier()
commander = None
trade_manager = None
regime_engine = None
sentiment_engine = None
trade_db = None

# Tracking
last_signal_check = {}
last_status_time = 0

def get_risk_engine(login):
    if login not in risk_engines:
        risk_engines[login] = RiskEngine(config, login=login)
    return risk_engines[login]

def run_trading_cycle():
    """
    Executes one full iteration of management and signal scanning across all accounts.
    """
    try:
        current_accounts = load_accounts()
        if not current_accounts:
            current_accounts = [bridge.master_credentials]

        # 1. RISK & TELEGRAM MONITORING
        for acc_creds in current_accounts:
            login = str(acc_creds['login'])
            if not bridge.switch_account(acc_creds):
                continue
            
            risk_engine = get_risk_engine(login)
            is_halted, should_liquidate, is_hard_down = risk_engine.check_daily_stop()
            
            if should_liquidate:
                print(f"🚨 CIRCUIT BREAKER TRIGGERED for {login}")
                positions = mt5.positions_get()
                if positions:
                    for pos in positions:
                        bridge.close_position(pos.ticket)
                notifier.send_message(f"🚨 *ACCOUNT CIRCUIT BREAKER ({login})*\nThreshold hit. Liquidating.")
                
            if is_hard_down:
                notifier.send_message(f"☢️ *SHUTDOWN ({login})*\n40% Drawdown reached.")
                risk_engine.halt_until = time.time() + 86400 * 365 

        if commander:
            commander.poll_commands()
            if commander.is_stopped:
                return

        # 2. MANAGEMENT
        focused_symbols = config.get('v5_settings', {}).get('focused_symbols', ["XAUUSD.m", "EURUSD.m"])
        strategies = {}
        for symbol in focused_symbols:
            mode = config.get('symbols', {}).get(symbol, {}).get('mode', config.get('mode', 'v5'))
            strategies[symbol] = get_strategy(mode, symbol, config)

        for acc_creds in current_accounts:
            if not bridge.switch_account(acc_creds): continue
            open_positions = mt5.positions_get()
            if open_positions:
                trade_manager.manage_open_positions(open_positions, strategies, regime_engine)

        # 3. SCANNING & EXECUTION
        # We use the first account as the "Master" for data feed consistency
        if not bridge.switch_account(current_accounts[0]): return
        
        for symbol, strategy in strategies.items():
            if symbol in last_signal_check and time.time() - last_signal_check[symbol] < 60:
                continue
            
            # Synchronous data fetching
            mtf_data = {
                'H4': bridge.get_data(symbol, mt5.TIMEFRAME_H4, 100),
                'H1': bridge.get_data(symbol, mt5.TIMEFRAME_H1, 100),
                'M15': bridge.get_data(symbol, mt5.TIMEFRAME_M15, 200),
                'M5': bridge.get_data(symbol, mt5.TIMEFRAME_M5, 200)
            }

            if any(df.empty for df in mtf_data.values()): continue

            regime = regime_engine.classify(mtf_data['M15'])
            
            # Sentiment check
            sentiment_boost = sentiment_engine.get_sentiment_boost(symbol)
            signal, reasoning = strategy.check_signal(mtf_data, sentiment_boost, regime)
            
            # 💓 Verbose Brain Heartbeat (Every 1 minute per symbol)
            pulse_msg = f"🧠 {symbol}: {reasoning}"
            print(pulse_msg)

            if signal:
                print(f"🎯 SIGNAL: {signal} {symbol}")
                # Execute for ALL accounts
                for acc_creds in current_accounts:
                    login = str(acc_creds['login'])
                    if not bridge.switch_account(acc_creds): continue
                    
                    risk_engine = get_risk_engine(login)
                    
                    # Custom War Room Lot Sizing
                    is_war_room = config.get('mode') == 'WAR_ROOM'
                    if is_war_room:
                        lot_size = 0.01 # Fixed for $100 experiment
                    else:
                        lot_size = risk_engine.calculate_lot_size(symbol, 1.0, 200)
                    
                    if not risk_engine.validate_portfolio_risk(symbol, 1.0): continue
                    
                    # 🏁 DUPLICATE GUARD: Check if position for symbol is already open
                    open_positions = mt5.positions_get(symbol=symbol)
                    if open_positions:
                        print(f"⏩ {symbol} Signal skipped: Position already open.")
                        continue

                    tick = mt5.symbol_info_tick(symbol)
                    if not tick: continue
                    
                    atr = calculate_atr(mtf_data['M15'])
                    entry = tick.ask if signal == 'BUY' else tick.bid
                    
                    # Trailing logic is handled by TradeManager, but SL/TP are initial
                    sl = entry - (atr * 2) if signal == 'BUY' else entry + (atr * 2)
                    tp = entry + (atr * 5) if signal == 'BUY' else entry - (atr * 5)
                    
                    result = bridge.send_order(symbol, mt5.ORDER_TYPE_BUY if signal == 'BUY' else mt5.ORDER_TYPE_SELL, lot_size, sl=sl, tp=tp)
                    if result:
                        notifier.send_message(f"🔥 [{login}] EXECUTED {signal} {symbol}")
                        # 📝 DB LOGGING
                        trade_db.log_trade_entry(
                            ticket=result.order,
                            symbol=symbol,
                            direction='BUY' if signal == 'BUY' else 'SELL',
                            entry_price=entry,
                            sl=sl,
                            tp=tp,
                            lot_size=lot_size,
                            regime=regime,
                            atr=atr,
                            strategy=strategy.name
                        )

            last_signal_check[symbol] = time.time()

        # No more pulse print here
    except Exception as e:
        print(f"❌ Cycle Error: {e}")
        traceback.print_exc()

def print_status_pulse():
    """
    Periodic status update to keep terminal alive and informative.
    """
    global last_status_time
    if time.time() - last_status_time < 30:
        return

    try:
        acc = mt5.account_info()
        pos_total = mt5.positions_total()
        if acc:
            focused_symbols = config.get('v5_settings', {}).get('focused_symbols', ["XAUUSD.m", "EURUSD.m"])
            status_line = f"Status: Scanning {len(focused_symbols)}... Equity: ${acc.equity:,.2f} | Balance: ${acc.balance:,.2f} | Open Trades: {pos_total} | Margin: ${acc.margin_free:,.2f} | Time: {time.strftime('%H:%M:%S')}"
            print(status_line)
        last_status_time = time.time()
    except Exception as e:
        print(f"⚠️ Status Pulse Error: {e}")

def main():
    global bridge, trade_manager, regime_engine, sentiment_engine, commander
    
    # 1. CLASSIC START STRINGS
    print("🚀 V3 Async Bot Starting...") 
    print("==================================================")
    print("🛡️ Risk Monitor Loop Started (100ms heartbeat)")
    print("⚡ Institutional Execution Loop Started (V5)")
    
    bridge = MT5Bridge(config)
    
    terminal_path = r"C:\Program Files\MT5 Weltrade\terminal64.exe"
    accounts = load_accounts()
    master = accounts[0] if accounts else bridge.master_credentials
    master_login = int(master.get('login', 0))
    master_password = master.get('password', '')
    master_server = master.get('server', '')

    print(f"🚀 Initializing MT5 for Master: {master_login}...")
    success = mt5.initialize(
        path=terminal_path,
        login=master_login,
        password=master_password,
        server=master_server
    )
    if not success:
        # Fallback: try basic init then explicit login
        print(f"⚠️ Integrated init failed {mt5.last_error()}, trying fallback login...")
        mt5.shutdown()
        success = mt5.initialize(path=terminal_path)
        if success:
            success = mt5.login(login=master_login, password=master_password, server=master_server)
    if not success:
        print(f"❌ [CRITICAL] Failed to initialize MT5: {mt5.last_error()}")
        return
    
    trade_db = TradeDB()
    trade_manager = TradeManager(config, bridge, notifier, trade_db)
    regime_engine = RegimeEngine(config)
    sentiment_engine = SentimentEngine(config)
    
    accounts = load_accounts()
    master_login = str(accounts[0]['login']) if accounts else str(bridge.master_credentials.get('login'))
    commander = TelegramCommander(bridge, get_risk_engine(master_login), notifier)
    
    # 2. CLASSIC SYMBOL SCANNING LOG
    focused_symbols = config.get('v5_settings', {}).get('focused_symbols', ["XAUUSD.m", "EURUSD.m"])
    print(f"🧠 Focused on {len(focused_symbols)} high-probability symbols")
    
    while True:
        run_trading_cycle()
        print_status_pulse()
        time.sleep(1.0) # Baseline pulse

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Shutdown")
    except Exception as e:
        print(f"❌ CRITICAL CRASH: {e}")
        traceback.print_exc()
