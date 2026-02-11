import json
import time
import MetaTrader5 as mt5
from execution.mt5_bridge import MT5Bridge
from strategies.gold_strategy import GoldInstitutionalStrategy
from strategies.btc_strategy import BTCInstitutionalStrategy
from strategies.forex_strategies import LondonBreakoutStrategy, CarryTrendStrategy, GBPJPYVolatilityStrategy
from strategies.scalp_strategy import ScalpStrategy
from regime_engine import RegimeEngine
from risk_engine import RiskEngine
from telegram_commander import TelegramCommander

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

# Track last failed order time per symbol to prevent spamming
# Debouncing: Prevent revenge trading and rapid re-entry
last_trade_time = {}
failure_cooldowns = {}

from ai_brain import AIBrain
from market_snapshot import MarketSnapshot
from telegram_notifer import TelegramNotifier
from datetime import datetime
import os

# Persistent memory for Post-Mortems
entry_snapshots = {}

# Initialize Components
config = load_config()
bridge = MT5Bridge(config)
risk_engine = RiskEngine(config)
brain = AIBrain()
notifier = TelegramNotifier()
commander = TelegramCommander(bridge, risk_engine, notifier)

def log_thought(symbol, action, thought_data):
    """
    Records the AI's internal monologue to a persistent log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{symbol}] ACTION: {action} | CONVICTION: {thought_data.get('conviction_score', 'N/A')}%\n"
    log_entry += f"REASONING: {thought_data.get('reasoning', 'N/A')}\n"
    if 'exit_strategy' in thought_data:
        log_entry += f"EXIT PLAN: {thought_data['exit_strategy']}\n"
    log_entry += "-" * 50 + "\n"
    
    with open("logs/thinking.log", "a") as f:
        f.write(log_entry)

# Track AI analysis frequency and daily counts
last_ai_check = {}
last_signal_check = {} # Cooldown for new signals
daily_scalp_count = {"date": datetime.now().date(), "count": 0}

def main():
    if not bridge.connect():
        return

    # Initialize strategies
    strategies = {}
    for symbol, settings in config['symbols'].items():
        if settings['enabled']:
            if "XAUUSD" in symbol:
                strategies[symbol] = GoldInstitutionalStrategy(symbol, config)
            elif "BTCUSD" in symbol:
                strategies[symbol] = BTCInstitutionalStrategy(symbol, config)
            elif "GBPUSD" in symbol:
                strategies[symbol] = LondonBreakoutStrategy(symbol, config)
            elif "USDJPY" in symbol:
                strategies[symbol] = CarryTrendStrategy(symbol, config)
            elif "GBPJPY" in symbol:
                strategies[symbol] = GBPJPYVolatilityStrategy(symbol, config)
            else:
                strategies[symbol] = ScalpStrategy(symbol, config)

    print("🧠 Thinking Agent Started. Local Confluence Brain & Telegram Integrated.")
    notifier.send_message("🚀 *Agentic Trading System Online*\nMode: Sniper Scalping (Max 3/day | 45s Throttle)")

    try:
        while True:
            # Reset daily counters
            today = datetime.now().date()
            if daily_scalp_count["date"] != today:
                daily_scalp_count["date"] = today
                daily_scalp_count["count"] = 0

            # 0. Telegram Overrides & Commands
            commander.poll_commands()
            
            # 0.5 Daily Loss Halt
            is_halted, should_liquidate = risk_engine.check_daily_stop()
            if is_halted:
                if should_liquidate:
                    positions = mt5.positions_get()
                    if positions:
                        print(f"🧨 [LIQUIDATION] Closing {len(positions)} positions due to 20% limit.")
                        for pos in positions:
                            bridge.close_position(pos.ticket)
                        notifier.send_message("🧨 *SYSTEM LIQUIDATION*\nAll positions closed due to 20% daily loss limit.")
                time.sleep(60)
                continue

            # 1. Global Checks
            if not mt5.terminal_info().trade_allowed or commander.is_stopped:
                time.sleep(10)
                continue
            # Safety Kill Switch Removed as per user request

            # 2. ACTIVE POSITION MANAGEMENT
            open_positions = mt5.positions_get()
            if open_positions:
                total_scalp_profit = 0
                scalp_found = []
                
                for pos in open_positions:
                    symbol = pos.symbol
                    strategy = strategies.get(symbol)
                    if not strategy: continue
                    
                    mode = "SCALPER" if isinstance(strategy, ScalpStrategy) else "INTRADAY"
                    
                    # 2.1 SCALP EXIT LOGIC (Capped Profit)
                    if mode == "SCALPER":
                        is_gold = "XAU" in symbol or "GOLD" in symbol
                        profit_target = 1.0 if is_gold else 0.5
                        if pos.profit >= profit_target:
                            print(f"💰 [SCALP TARGET] {symbol} hit ${pos.profit:.2f}. Closing.")
                            if bridge.close_position(pos.ticket):
                                notifier.send_message(f"💰 *Scalp Target Hit ({symbol})*\nPnL: ${pos.profit:.2f}")
                            continue
                    
                    # 2.2 INTRADAY BE LOGIC (Dynamic ATR-Based)
                    elif mode == "INTRADAY":
                        # Fetch M1 Data for Volatility Calc (Efficient Single Call)
                        # We use a short cache or direct call as it's critical logic
                        m1_data = bridge.get_data(symbol, mt5.TIMEFRAME_M1, 20)
                        
                        if not m1_data.empty and len(m1_data) > 15:
                            from indicators import calculate_atr
                            current_atr = calculate_atr(m1_data)
                            
                            # BE Settings
                            be_mult = config['risk_management'].get('be_trigger_atr_multiple', 1.5)
                            be_buffer = config['risk_management'].get('be_buffer_points', 50) * mt5.symbol_info(symbol).point
                            
                            trigger_dist = current_atr * be_mult
                            
                            current_dist = abs(pos.price_current - pos.price_open)
                            
                            # Only Trigger if positive profit and distance met
                            if pos.profit > 0 and current_dist > trigger_dist:
                                entry_price = pos.price_open
                                current_sl = pos.sl
                                is_buy = pos.type == mt5.ORDER_TYPE_BUY
                                
                                # Targeted SL: Entry + Buffer to cover fees
                                new_sl = entry_price + be_buffer if is_buy else entry_price - be_buffer
                                
                                # Check if SL is already better than what we plan
                                sl_improved = (is_buy and current_sl < new_sl) or (not is_buy and current_sl > new_sl)
                                
                                if sl_improved:
                                    if bridge.modify_position_sl(pos.ticket, new_sl):
                                        notifier.send_message(f"🛡️ *{symbol} Secured to BE*\nTrigger: {current_dist:.5f} > {trigger_dist:.5f} (ATR * {be_mult})")

                    # AI Re-evaluation (Early Exit / BE)
                    # RADICAL COST SAVING THROTTLE: Only re-evaluate every 3-5 mins
                    throttle = 180 if isinstance(strategy, ScalpStrategy) else 600
                    if symbol in last_ai_check and time.time() - last_ai_check[symbol] < throttle:
                        continue
                    last_ai_check[symbol] = time.time()

                    mtf_data = bridge.get_mtf_data(symbol)
                    regime = strategy.regime_engine.classify(mtf_data['M1'])
                    snapshot = MarketSnapshot.get_narrative(symbol, mtf_data['M1'], mtf_data['H4'], regime)
                    
                    mode = "SCALPER" if isinstance(strategy, ScalpStrategy) else "INTRADAY"
                    decision = brain.evaluate_open_position(snapshot, pos.profit, mode=mode)
                    
                    # LIVE LEARNING / INTERVENTION
                    # Trigger if specifically requested OR if in significant drawdown
                    if commander.pending_learning_trigger or pos.profit < -1.50:
                        entry_shot = entry_snapshots.get(pos.ticket, "Unknown Entry State (Pre-Overhaul)")
                        print(f"🧠 [INTERVENTION] Analyzing open trade drawdown for {symbol}...")
                        intervention = brain.analyze_live_drawdown(symbol, entry_shot, snapshot, pos.profit)
                        if intervention:
                            notifier.send_message(f"🎓 *LIVE LESSON LEARNED ({symbol})*\nMistake: {intervention['mistake']}\nLesson: {intervention['lesson']}")
                            if intervention.get('intervention') == 'CUT_LOSS':
                                if bridge.close_position(pos.ticket):
                                    notifier.send_message(f"🧨 *AI EMERGENCY CUT* for {symbol}\nReasoning: Found fundamental mistake in setup.")
                                    continue # Skip further logic for this pos
                    
                    if decision['decision'] == 'MOVE_TO_BE':
                        entry_price = pos.price_open
                        current_sl = pos.sl
                        is_buy = pos.type == mt5.ORDER_TYPE_BUY
                        if (is_buy and current_sl < entry_price) or (not is_buy and current_sl > entry_price):
                            if bridge.modify_position_sl(pos.ticket, entry_price):
                                notifier.send_message(f"🛡️ *{symbol} Moved to Break-Even*\nPnL: ${pos.profit:.2f}")

                    elif decision['decision'] in ['TAKE_PROFIT', 'CUT_LOSS']:
                        pnl = pos.profit
                        if bridge.close_position(pos.ticket):
                            notifier.send_message(f"✅ *{mode} Early Exit ({symbol})*\nReason: {decision['reasoning']}")
                            
                            # POST-MORTEM (Learning Loop)
                            if pnl < 0:
                                entry_shot = entry_snapshots.get(pos.ticket, "Unknown Entry State")
                                print(f"🧠 [LEARNING] Analyzing failed trade ({symbol}, PnL: ${pnl:.2f})...")
                                lesson = brain.analyze_loss(symbol, entry_shot, snapshot, pnl)
                                if lesson:
                                    notifier.send_message(f"🎓 *AI LESSON LEARNED ({symbol})*\n_{lesson['lesson']}_")
                            
                            if pos.ticket in entry_snapshots: del entry_snapshots[pos.ticket]

                # 4. GHOST TRADES SCAN (Closed by SL/TP)
                active_tickets = [p.ticket for p in open_positions]
                ghosts = [t for t in entry_snapshots.keys() if t not in active_tickets]
                
                for ghost_ticket in ghosts:
                    # Fetch deal from history to get PnL
                    deals = mt5.history_deals_get(ticket=ghost_ticket)
                    if deals:
                        for deal in deals:
                            if deal.entry == mt5.DEAL_ENTRY_OUT:
                                pnl = deal.profit
                                symbol = deal.symbol
                                if pnl < 0:
                                    print(f"👻 [GHOST] Detected SL hit for {symbol} (PnL: ${pnl:.2f}). Analyzing...")
                                    entry_shot = entry_snapshots[ghost_ticket]
                                    lesson = brain.analyze_loss(symbol, entry_shot, "Closed by Server (SL/TP)", pnl)
                                    if lesson:
                                        notifier.send_message(f"🎓 *SERVER-SIDE LOSS LESSON ({symbol})*\n_{lesson['lesson']}_")
                    del entry_snapshots[ghost_ticket]
                
                # Reset the learning trigger after processing all positions
                commander.pending_learning_trigger = False
            for symbol, strategy in strategies.items():
                if not bridge.is_market_open(symbol):
                    print(f"DEBUG: {symbol} market closed or no fresh ticks.")
                    continue

                # Fetch Multi-Timeframe Data
                # DEBOUNCING: If recently closed or REJECTED, wait 15 mins (20 mins for intraday)
                lockout = 300 if isinstance(strategy, ScalpStrategy) else 1200 
                if symbol in last_trade_time and time.time() - last_trade_time[symbol] < lockout:
                    # print(f"DEBUG: {symbol} in lockout.")
                    continue
                
                # Signal Cooldown (Even if rejected by AI, wait 10 mins before asking again)
                if symbol in last_signal_check and time.time() - last_signal_check[symbol] < 600:
                    # print(f"DEBUG: {symbol} in signal cooldown.")
                    continue

                # Sniper Limit: Only 3 scalps per day
                if isinstance(strategy, ScalpStrategy) and daily_scalp_count["count"] >= 3:
                    # print(f"DEBUG: {symbol} scalp limit reached.")
                    continue

                mtf_data = bridge.get_mtf_data(symbol)
                if mtf_data['M1'].empty or len(mtf_data['M1']) < 200:
                    print(f"DEBUG: {symbol} data empty or insufficient ({len(mtf_data['M1'])}).")
                    continue

                # Standard technical signal
                signal = strategy.check_signal(mtf_data['M1'])
                
                if signal in ['BUY', 'SELL']:
                    mode = "SCALPER" if isinstance(strategy, ScalpStrategy) else "INTRADAY"
                    lot_size, max_pos = risk_engine.get_session_params(symbol, mode)
                    
                    # Session-aware monitoring
                    if bridge.get_open_position_count(symbol) >= max_pos:
                        continue

                    regime = strategy.regime_engine.classify(mtf_data['M1'])
                    snapshot = MarketSnapshot.get_narrative(symbol, mtf_data['M1'], mtf_data['H4'], regime)
                    
                    print(f"🔍 [{symbol}] Technical Signal ({mode}): {signal}. Consulting Brain...")
                    thought_data = brain.analyze_setup(snapshot, mode=mode)
                    
                    log_thought(symbol, f"ANALYSIS_{mode}_{signal}", thought_data)

                    if thought_data.get('action') == "PROCEED" and thought_data.get('conviction_score', 0) > 60:
                        print(f"🔥 [{symbol}] High Conviction ({thought_data['conviction_score']}%). Opening Session...")
                        
                        order_type = mt5.ORDER_TYPE_BUY if signal == 'BUY' else mt5.ORDER_TYPE_SELL
                        
                        # Execute Burst/Session
                        # Use AI's suggested count if available, otherwise use risk-max
                        ai_count = thought_data.get('suggested_positions', 1)
                        session_size = min(ai_count, max_pos)
                        
                        print(f"🔥 [{symbol}] High Conviction. Opening Session of {session_size} positions...")
                        
                        success_count = 0
                        for _ in range(session_size):
                            # For Intraday, AI provides TP/SL
                            sl = thought_data.get('sl') if mode == "INTRADAY" else None
                            tp = thought_data.get('tp') if mode == "INTRADAY" else None
                            
                            ticket = bridge.send_order(symbol, order_type, lot_size, sl=sl, tp=tp)
                            if ticket:
                                success_count += 1
                                # Capture Entry State for future Post-Mortems
                                if isinstance(ticket, int):
                                    entry_snapshots[ticket] = snapshot
                                elif isinstance(ticket, dict) and 'ticket' in ticket:
                                    entry_snapshots[ticket['ticket']] = snapshot
                            time.sleep(0.15) # Safety delay
                        
                        if success_count > 0:
                            # Send elite trade alert
                            last_price = bridge.get_mtf_data(symbol)['M1']['close'].iloc[-1]
                            notifier.send_trade_alert(symbol, signal, last_price, mode=mode, session_count=success_count if mode == "SCALPER" else None)
                            
                            if mode == "SCALPER":
                                daily_scalp_count["count"] += 1
                                last_trade_time[symbol] = time.time()
                                notifier.send_thought(symbol, thought_data['reasoning'], thought_data['conviction_score'], mode=mode)
                            else:
                                last_trade_time[symbol] = time.time()
                                notifier.send_thought(symbol, thought_data['reasoning'], thought_data['conviction_score'], mode=mode)
                    else:
                        print(f"✋ [{symbol}] AI rejected setup (Conviction: {thought_data.get('conviction_score', 0)}%). Reason: {thought_data.get('reasoning')}")
                        # Set a signal lockout so we don't ask the AI about this same rejection for a while
                        last_signal_check[symbol] = time.time()

            time.sleep(2) # Breathable loop
            
    except KeyboardInterrupt:
        print("Bot stopped.")
    finally:
        bridge.disconnect()

if __name__ == "__main__":
    main()
