import MetaTrader5 as mt5
import time
import os

class RiskEngine:
    def __init__(self, config, login=None):
        self.config = config
        self.login = login
        self.halt_until = 0
        self.peak_equity = 0.0 # High-Water Mark tracking
        self.state_file = os.path.join("config", f"risk_state_{login}.json") if login else None
        self._load_state()

    def _load_state(self):
        """Load persistent risk state"""
        if self.state_file and os.path.exists(self.state_file):
            try:
                import json
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.peak_equity = state.get('peak_equity', 0.0)
                    self.halt_until = state.get('halt_until', 0)
            except:
                pass

    def _save_state(self):
        """Save persistent risk state"""
        if self.state_file:
            try:
                import json
                os.makedirs("config", exist_ok=True)
                with open(self.state_file, 'w') as f:
                    json.dump({
                        'peak_equity': self.peak_equity,
                        'halt_until': self.halt_until
                    }, f)
            except:
                pass

    def update_peak_equity(self):
        """Update HWM session peak"""
        account_info = mt5.account_info()
        if account_info:
            if account_info.equity > self.peak_equity:
                self.peak_equity = account_info.equity
                self._save_state()

    def calculate_lot_size(self, symbol, risk_percent, stop_loss_points):
        """
        Adaptive Lot Sizing Logic (V7 Rescue Mode):
        - Forced 0.01 for Account Recovery ($45 scenario).
        - Standard institutional scaling for balance > $500.
        """
        account_info = mt5.account_info()
        if not account_info: return 0.01
        
        balance = account_info.balance
        equity = account_info.equity
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info: return 0.01

        # 1. SPECIAL CASE: Recovery Mode (Below $100)
        if equity < 100:
            return 0.01 # Recovery Mode: Forced micro-lot

        is_volatile = any(x in symbol.upper() for x in ["XAU", "BTC", "ETH", "SOL", "BNB"])
        
        # 2. Conservative cap for Volatiles
        if is_volatile:
            if equity < 200: return 0.01 # Stay micro for volatiles on small accounts
            return 0.02 # Capped aggression

        # 3. Standard Institutional Mode (V5)
        # Risk 0.5% - 1.5% per trade via ATR-based calculation
        # lot_size = (balance * risk_percent) / (stop_loss_points * tick_value)
        
        base_lots = 0.03 # Starting lot for V5 ($100+ accounts)
        if equity > 500:
            base_lots = 0.05
        if equity < (balance * 0.85): # Drawdown guard
            base_lots = 0.01
            
        lot_step = symbol_info.volume_step
        lot_size = max(symbol_info.volume_min, min(base_lots, symbol_info.volume_max))
        lot_size = round(lot_size / lot_step) * lot_step
        
        return round(lot_size, 2)


    def validate_portfolio_risk(self, symbol, risk_percent):
        """
        Check Portfolio Heat and Correlation Caps (15% Heat Limit)
        """
        positions = mt5.positions_get()
        current_risk = 0
        if positions:
            for pos in positions:
                current_risk += 1.5 # Fixed 1.5% assumption per open position for heat tracking

        max_heat = self.config['risk_management'].get('max_open_risk_percent', 15.0)
        if (current_risk + risk_percent) > max_heat:
            print(f"⚠️ [PORTFOLIO] Max Heat Reached: {current_risk}% + {risk_percent}% > {max_heat}%")
            return False

        base_curr = symbol[:3]
        basket_risk = 0
        if positions:
            for pos in positions:
                if pos.symbol.startswith(base_curr):
                    basket_risk += 1.5
        
        max_basket = self.config['risk_management'].get('max_currency_risk_percent', 10.0)
        if (basket_risk + risk_percent) > max_basket:
            print(f"⚠️ [PORTFOLIO] {base_curr} Basket Full: {basket_risk}% + {risk_percent}% > {max_basket}%")
            return False
            
        return True

    def check_daily_stop(self):
        """
        HWM PROTECTED CIRCUIT BREAKER (V7.1)
        Returns (is_halted, should_liquidate, is_hard_down)
        """
        if time.time() < self.halt_until:
            return True, False, False

        account_info = mt5.account_info()
        if not account_info: return True, False, False
        
        # 1. Update High-Water Mark
        self.update_peak_equity()
        
        # 2. Calculate Drawdown from PEAK (HWM)
        if self.peak_equity > 0:
            hwm_drawdown = ((self.peak_equity - account_info.equity) / self.peak_equity) * 100
        else:
            hwm_drawdown = 0

        # Also track standard daily drawdown from balance
        balance_drawdown = ((account_info.balance - account_info.equity) / account_info.balance) * 100
        
        # 🟡 PHASE 1: Caution (11% HWM Drawdown) - Halt New Entries
        caution_limit = 11.0 # Tightened from 15.0
        if hwm_drawdown >= caution_limit and hwm_drawdown < 23.0:
            print(f"⚠️ [CAUTION] 11% HWM Drawdown Hit ({hwm_drawdown:.2f}% from peak). Cooling off 4h.")
            self.halt_until = time.time() + 14400 
            self._save_state()
            return True, False, False

        # 🟠 PHASE 2: Emergency (23% HWM Drawdown) - Liquidate + 24hr Halt
        # Special War Room override: 50% Hard Stop
        is_war_room = self.config.get('mode') == 'WAR_ROOM'
        emergency_limit = 50.0 if is_war_room else 23.0 
        
        if hwm_drawdown >= emergency_limit or balance_drawdown >= emergency_limit:
            print(f"🚨 [{'WAR ROOM' if is_war_room else 'EMERGENCY'}] {emergency_limit}% Drawdown Hit. Liquidating.")
            self.halt_until = time.time() + 86400 
            self._save_state()
            return True, True, False

        # 🔴 PHASE 3: Nuclear (40% Total Drawdown) - Hard Bot Shutdown
        if balance_drawdown >= 40.0 and not is_war_room:
            print(f"☢️ [NUCLEAR] 40% Total Drawdown Hit. HARD SHUTDOWN.")
            return True, True, True

        return False, False, False

    def current_risk(self):
        """Calculates total portfolio heat (risk %)"""
        positions = mt5.positions_get()
        risk = 0
        if positions:
            for _ in positions:
                risk += 1.5 # Assumption per open trade
        return round(risk, 2)

    def get_today_drawdown(self):
        """Returns the current drawdown from session peak as a percentage."""
        account_info = mt5.account_info()
        if not account_info or self.peak_equity <= 0:
            return 0.0
        dd = ((self.peak_equity - account_info.equity) / self.peak_equity) * 100
        return round(max(0, dd), 2)
