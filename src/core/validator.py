"""
Math Validator - Gatekeeper for all trade orders
Rejects impossible or invalid orders before they reach MT5
"""
import MetaTrader5 as mt5

class Validator:
    def __init__(self, config):
        self.config = config
        self.min_rr_ratio = 1.35  # Relaxed from 2.0 to accommodate spread on 1.5 Target (TP3.0/SL2.0)
    
    def _get_min_rr(self, symbol):
        """Symbol-aware RR minimum. Crypto uses wider ATR-scaled stops."""
        if any(x in symbol.upper() for x in ["BTC", "ETH", "XRP", "SOL", "BNB"]):
            return 1.25  # Crypto: wide stops, still positive expectancy
        return self.min_rr_ratio  # Forex: strict 1.35

    def validate_order(self, symbol, order_type, entry, sl, tp, lot):
        """
        Validates order parameters before execution
        Returns (is_valid, error_message)
        """
        
        # 1. Check SL on correct side
        if order_type == mt5.ORDER_TYPE_BUY:
            if sl >= entry:
                return False, f"Invalid SL for BUY: {sl} >= {entry}"
        else:  # SELL
            if sl <= entry:
                return False, f"Invalid SL for SELL: {sl} <= {entry}"
        
        # 2. Check TP on correct side
        if order_type == mt5.ORDER_TYPE_BUY:
            if tp <= entry:
                return False, f"Invalid TP for BUY: {tp} <= {entry}"
        else:  # SELL
            if tp >= entry:
                return False, f"Invalid TP for SELL: {tp} >= {entry}"
        
        # 3. Minimum RR ratio check
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        
        if risk == 0:
            return False, "Risk is zero (SL == Entry)"
        
        rr_ratio = reward / risk
        min_rr = self._get_min_rr(symbol)
        if rr_ratio < (min_rr - 0.01):
            return False, f"RR ratio too low: {rr_ratio:.2f} < {min_rr}"
        
        # 4. Check minimum stop distance
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return False, f"Cannot get symbol info for {symbol}"
        
        min_stop_distance = symbol_info.trade_stops_level * symbol_info.point
        
        if risk < min_stop_distance:
            return False, f"Stop distance {risk:.5f} < minimum {min_stop_distance:.5f}"
        
        # 5. Check lot size is valid
        if lot < symbol_info.volume_min:
            return False, f"Lot size {lot} < minimum {symbol_info.volume_min}"
        
        if lot > symbol_info.volume_max:
            return False, f"Lot size {lot} > maximum {symbol_info.volume_max}"
        
        # 6. Check lot size within account risk limits
        # [REMOVED FOR MAX AGGRESSION] - Global Safety Net handles this now
        # account_info = mt5.account_info()
        # if account_info:
        #     max_risk_percent = self.config['risk_management'].get('max_risk_per_trade_percent', 2.0)
        #     max_risk_amount = account_info.equity * (max_risk_percent / 100.0)
        #     risk_in_dollars = (risk / symbol_info.point) * (symbol_info.trade_tick_value / (symbol_info.trade_tick_size / symbol_info.point)) * lot
        #     if risk_in_dollars > (max_risk_amount * 1.1):
        #         return False, f"Risk ${risk_in_dollars:.2f} > max allowed (at min lot) ${max_risk_amount:.2f}"
        
        return True, "Valid"
    
    def validate_sl_modification(self, position, new_sl):
        """
        Validates SL modification
        Returns (is_valid, error_message)
        """
        is_buy = position.type == mt5.ORDER_TYPE_BUY
        
        # Check SL is on correct side
        if is_buy and new_sl >= position.price_current:
            return False, f"New SL {new_sl} >= current price {position.price_current}"
        
        if not is_buy and new_sl <= position.price_current:
            return False, f"New SL {new_sl} <= current price {position.price_current}"
        
        # Check SL is improving (moving towards BE or better)
        if is_buy:
            if new_sl < position.sl:
                return False, f"New SL {new_sl} worse than current {position.sl}"
        else:
            if new_sl > position.sl:
                return False, f"New SL {new_sl} worse than current {position.sl}"
        
        return True, "Valid"
