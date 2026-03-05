"""
Portfolio Manager - Tracks correlation and total exposure
Prevents overexposure to correlated positions
"""
import MetaTrader5 as mt5

class Portfolio:
    def __init__(self, config):
        self.config = config
        self.max_total_risk_percent = config['risk_management'].get('max_total_exposure_percent', 5.0)
        
        # Correlation groups (simplified)
        self.correlation_groups = {
            'USD_LONG': ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'],  # All are USD pairs
            'USD_SHORT': ['USDJPY', 'USDCHF', 'USDCAD'],
            'EUR': ['EURUSD', 'EURJPY', 'EURGBP', 'EURAUD'],
            'GBP': ['GBPUSD', 'GBPJPY', 'EURGBP'],
            'GOLD': ['XAUUSD'],
            'BTC': ['BTCUSD']
        }
    
    def get_total_risk_percent(self):
        """
        Calculate total risk across all open positions
        Returns risk as percentage of equity
        """
        positions = mt5.positions_get()
        if not positions:
            return 0.0
        
        account_info = mt5.account_info()
        if not account_info or account_info.equity == 0:
            return 0.0
        
        total_risk = 0.0
        
        for pos in positions:
            # Calculate risk per position (entry to SL distance)
            if pos.type == mt5.ORDER_TYPE_BUY:
                risk_distance = abs(pos.price_open - pos.sl)
            else:
                risk_distance = abs(pos.sl - pos.price_open)
            
            # Get symbol info for tick value
            symbol_info = mt5.symbol_info(pos.symbol)
            if symbol_info:
                # Approximate risk in dollars
                risk_dollars = risk_distance / symbol_info.point * symbol_info.trade_tick_value * pos.volume
                total_risk += risk_dollars
        
        # Return as percentage of equity
        return (total_risk / account_info.equity) * 100.0
    
    def get_directional_exposure(self, symbol, direction):
        """
        Get current exposure in the same direction for correlated pairs
        Returns count of correlated positions
        """
        positions = mt5.positions_get()
        if not positions:
            return 0
        
        # Find which correlation group this symbol belongs to
        symbol_groups = []
        for group_name, symbols in self.correlation_groups.items():
            if any(s in symbol for s in symbols):
                symbol_groups.append(group_name)
        
        if not symbol_groups:
            return 0
        
        # Count positions in same direction within correlation groups
        correlated_count = 0
        
        for pos in positions:
            pos_direction = 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
            
            # Check if position is in same correlation group and direction
            for group_name in symbol_groups:
                if any(s in pos.symbol for s in self.correlation_groups[group_name]):
                    if pos_direction == direction:
                        correlated_count += 1
                        break
        
        return correlated_count
    
    def check_can_add_position(self, symbol, direction):
        """
        Check if we can add a new position without exceeding limits
        Returns (can_add, reason)
        """
        # 1. Check total risk limit
        current_risk = self.get_total_risk_percent()
        if current_risk >= self.max_total_risk_percent:
            return False, f"Total risk {current_risk:.1f}% >= max {self.max_total_risk_percent}%"
        
        # 2. Check correlation limit (max 3 correlated positions)
        correlated_count = self.get_directional_exposure(symbol, direction)
        if correlated_count >= 3:
            return False, f"Already {correlated_count} correlated {direction} positions"
        
        # 3. Check Currency Basket Risk (max 2% per base currency)
        # Simplified: Check how many positions share the same base currency (first 3 chars)
        base_curr = symbol[:3]
        
        # Exception: BTC and XAU trade independently of forex baskets
        if base_curr not in ["BTC", "XAU"]:
            positions = mt5.positions_get()
            basket_count = 0
            if positions:
                for pos in positions:
                    if pos.symbol.startswith(base_curr):
                        basket_count += 1
            
            if basket_count >= 2: # Max 2 trades per base currency (e.g., max 2 USD trades)
                return False, f"{base_curr} basket full ({basket_count} positions)"
        
        return True, "OK"

