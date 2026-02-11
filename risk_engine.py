import MetaTrader5 as mt5

class RiskEngine:
    def __init__(self, config):
        self.config = config
        self.max_dd = config['risk_management']['daily_loss_limit_percent']
        self.max_exposure = config['risk_management']['max_total_exposure_percent']

    def get_session_params(self, symbol, mode):
        """
        Returns (lot_size, max_positions) for a specific trading session.
        Enforces strict Gold constraints and dynamic currency scaling.
        """
        account_info = mt5.account_info()
        balance = account_info.balance if account_info else 1000.0
        
        is_gold = "XAU" in symbol or "GOLD" in symbol
        
        # 1. LOT SIZING
        if is_gold:
            # Strict Gold Rule: 0.01 or 0.02 ONLY
            lot_size = 0.02 if balance > 500 else 0.01
        else:
            # Currency/Other Scaling: 0.05 to 0.10
            # Base logic: 0.1 per $1000, capped at 0.1
            calc_lots = (balance / 1000.0) * 0.1
            lot_size = max(0.05, min(round(calc_lots, 2), 0.10))

        # 2. POSITION LIMITS (Sessions)
        if mode == "SCALPER":
            # Scalp Sessions: Up to 10 for Gold, 20 for Currencies
            max_positions = 10 if is_gold else 20
        else:
            # Intraday: Max 2 for Gold, otherwise unlimited (let brain decide)
            max_positions = 2 if is_gold else 5 # Defaulting to 5 for security, brain can request more

        print(f"🛡️ [RISK] {symbol} ({mode}) -> Lots: {lot_size}, Max Pos: {max_positions}")
        return lot_size, max_positions

    def check_daily_stop(self):
        """
        Checks if the account has reached its daily loss limit.
        Returns (is_halted, should_liquidate)
        """
        account_info = mt5.account_info()
        if not account_info: return True, False # Safety stop if error
        
        limit_percent = self.config['risk_management'].get('daily_loss_limit_percent', 20.0)
        drawdown = ((account_info.balance - account_info.equity) / account_info.balance) * 100
        
        if drawdown >= limit_percent:
            print(f"🛑 [HALT] Daily Loss Limit Reached ({drawdown:.2f}%). Triggering Liquidation.")
            return True, True
        return False, False

