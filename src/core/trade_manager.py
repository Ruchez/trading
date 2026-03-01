import MetaTrader5 as mt5
import pandas as pd
from src.utils.market_math import calculate_atr

class TradeManager:
    """
    Advanced Trade Management for V5.
    Handles dynamic trailing, regime-aware exits, and pyramid execution.
    """
    def __init__(self, config, bridge, notifier):
        self.config = config
        self.bridge = bridge
        self.notifier = notifier

    def manage_open_positions(self, positions, strategies, regime_engine):
        """
        Main entry point for position management in Execution Loop.
        """
        for pos in positions:
            symbol = pos.symbol
            if symbol not in strategies:
                continue

            strategy = strategies[symbol]
            mtf_data = self.bridge.get_mtf_data(symbol)
            if mtf_data['M1'].empty:
                continue

            # 1. Check for Early Exits (Regime Shift / Momentum Fade)
            should_exit, reason = self.check_early_exit(pos, mtf_data, regime_engine)
            if should_exit:
                if self.bridge.close_position(pos.ticket):
                    self.notifier.send_message(f"🏃 *{symbol} Early Exit*\nReason: {reason}")
                continue

            # 2. Advanced Trailing / BE Logic
            self.apply_trailing_logic(pos, mtf_data)

    def check_early_exit(self, pos, mtf_data, regime_engine):
        """
        Determines if a position should be closed before SL/TP hit.
        """
        current_regime = regime_engine.classify(mtf_data['M15'])
        
        # Rule: Exit trend continuation trades if regime becomes 'Choppy'
        if current_regime == 'CHOPPY':
            return True, "Market shifted to CHOPPY regime."

        return False, None

    def apply_trailing_logic(self, pos, mtf_data):
        """
        Implements profit-staircase trailing.
        """
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        entry = pos.price_open
        current = pos.price_current
        tp = pos.tp
        sl = pos.sl

        if tp == 0: return # No math possible without TP

        # Calculate R-multiples
        risk_dist = abs(entry - sl)
        if risk_dist <= 0: return
        
        profit_dist = (current - entry) if is_buy else (entry - current)
        r_multiple = profit_dist / risk_dist

        # 1. Move to BE @ 1.0R
        if r_multiple >= 1.0 and abs(sl - entry) > 0.0001: 
             # Only move if not already at BE
             is_already_be = (is_buy and sl >= entry) or (not is_buy and sl <= entry)
             if not is_already_be:
                 symbol_info = mt5.symbol_info(pos.symbol)
                 if symbol_info:
                    new_sl = entry + (5 * symbol_info.point) if is_buy else entry - (5 * symbol_info.point)
                    self.bridge.modify_position_sl(pos.ticket, new_sl)
                    self.notifier.send_message(f"🛡️ *{pos.symbol} Secured to BE (1.0R hit)*")
                    return

        # 2. Trail by ATR @ 1.5R+
        if r_multiple >= 1.5:
            atr = calculate_atr(mtf_data['M15'])
            
            # War Room Specific: Ultra-tight trailing (0.5x ATR)
            is_war_room = self.config.get('mode') == 'WAR_ROOM'
            mult = 0.5 if is_war_room else 1.5
            
            trail_dist = atr * mult
            
            new_sl = current - trail_dist if is_buy else current + trail_dist
            
            # Ensure trail only moves in one direction (improves)
            symbol_info = mt5.symbol_info(pos.symbol)
            if symbol_info:
                if is_buy:
                    if new_sl > pos.sl + (symbol_info.point * 10):
                        self.bridge.modify_position_sl(pos.ticket, new_sl)
                else:
                    if new_sl < pos.sl - (symbol_info.point * 10):
                        self.bridge.modify_position_sl(pos.ticket, new_sl)
