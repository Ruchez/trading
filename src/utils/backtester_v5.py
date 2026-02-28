import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.strategies.institutional_v5 import InstitutionalStrategyV5
from src.utils.market_math import calculate_atr
import matplotlib.pyplot as plt

class BacktesterV5:
    """
    High-Fidelity Backtester for V5 Institutional Strategy.
    Simulates execution over historical MT5 data.
    """
    def __init__(self, bridge, config, initial_balance=None):
        self.bridge = bridge
        self.config = config
        self.results = []
        
        # 1. Use actual equity if not specified
        if initial_balance is None:
            account_info = mt5.account_info()
            self.initial_balance = account_info.equity if account_info else 10000.0
        else:
            self.initial_balance = initial_balance
            
        self.equity_curve = []

    def _convert_to_datetime(self, t):
        """Helper to ensure we have a displayable datetime-like object."""
        if isinstance(t, (int, float, np.int64)):
            return datetime.fromtimestamp(t)
        return t # Assume pandas Timestamp or datetime

    def run(self, symbol, days=365):
        """
        Runs the backtest for a specific symbol.
        """
        print(f"\n⌛ Starting {days}-Day ({round(days/365, 1)}y) Backtest for {symbol}...")
        print(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
        
        # 1. Fetch Data
        print("📥 Fetching historical data (this may take a minute for large periods)...")
        # Days to bars approximation
        # We fetch slightly more to allow for indicator warm-up at the start
        h4_bars = days * 6 + 200
        h1_bars = days * 24 + 300
        m15_bars = days * 96 + 500
        m5_bars = days * 288 + 1000

        data_h4 = self.bridge.get_data(symbol, mt5.TIMEFRAME_H4, h4_bars)
        data_h1 = self.bridge.get_data(symbol, mt5.TIMEFRAME_H1, h1_bars)
        data_m15 = self.bridge.get_data(symbol, mt5.TIMEFRAME_M15, m15_bars)
        data_m5 = self.bridge.get_data(symbol, mt5.TIMEFRAME_M5, m5_bars)

        # Validation: Check which TFs returned data
        tf_check = {
            'H4': len(data_h4), 'H1': len(data_h1),
            'M15': len(data_m15), 'M5': len(data_m5)
        }
        
        for tf, count in tf_check.items():
            if count < 100: # Threshold for meaningful backtest
                print(f"❌ Insufficient {tf} data for {symbol} ({count} bars). MT5 history might be limited.")
                return None
            print(f"✅ {tf} data: {count} bars loaded.")

        # Find the common start time where all data exists
        latest_start = max(
            data_h4['time'].iloc[0],
            data_h1['time'].iloc[0],
            data_m15['time'].iloc[0],
            data_m5['time'].iloc[0]
        )
        
        # Trim M15 (our anchor) to start from the latest_start
        data_m15 = data_m15[data_m15['time'] >= latest_start].reset_index(drop=True)
        print(f"📅 Simulation start: {self._convert_to_datetime(latest_start)}")

        # Initialize Strategy
        strategy = InstitutionalStrategyV5(symbol, self.config)
        balance = self.initial_balance
        self.equity_curve = [balance]
        
        open_trade = None
        trades = []

        # 2. Simulation Loop (Using M15 as the anchor for efficiency)
        total_steps = len(data_m15)
        
        print("⚙️ Simulating...")
        # Progress Tracking
        for i in range(200, total_steps): # Start after indicator warm-up
            current_time = data_m15['time'].iloc[i]
            
            # Slice data up to current_time (Using tail for efficiency in lookups)
            mtf_data = {
                'H4': data_h4[data_h4['time'] <= current_time].tail(100),
                'H1': data_h1[data_h1['time'] <= current_time].tail(200),
                'M15': data_m15[data_m15['time'] <= current_time].tail(300),
                'M5': data_m5[data_m5['time'] <= current_time].tail(300)
            }

            # --- Check Exit for Open Trade ---
            if open_trade:
                row = data_m15.iloc[i]
                is_buy = open_trade['type'] == 'BUY'
                
                # Check Stop Loss
                hit_sl = (is_buy and row['low'] <= open_trade['sl']) or \
                         (not is_buy and row['high'] >= open_trade['sl'])
                
                # Check Take Profit
                hit_tp = (is_buy and row['high'] >= open_trade['tp']) or \
                         (not is_buy and row['low'] <= open_trade['tp'])

                if hit_sl or hit_tp:
                    pnl = open_trade['risk_dollars'] * (open_trade['tp_multiplier']) if hit_tp else -open_trade['risk_dollars']
                    balance += pnl
                    self.equity_curve.append(balance)
                    
                    trades.append({
                        'entry_time': self._convert_to_datetime(open_trade['time']),
                        'exit_time': self._convert_to_datetime(current_time),
                        'type': open_trade['type'],
                        'pnl': pnl,
                        'reason': 'TP' if hit_tp else 'SL'
                    })
                    open_trade = None

            # --- Check Entry ---
            if not open_trade:
                signal, reason = strategy.check_signal(mtf_data, sentiment_boost=0, regime='TRENDING') 
                
                if signal:
                    entry_price = data_m15['close'].iloc[i]
                    atr = calculate_atr(mtf_data['M15'])
                    
                    risk_percent = self.config['risk_management'].get('max_risk_per_trade_percent', 1.0) / 100.0
                    risk_dollars = balance * risk_percent
                    
                    # V5 Parameters: 2x ATR SL, 5x ATR TP (2.5:1 RR)
                    tp_multiplier = 2.5
                    sl = entry_price - (atr * 2) if signal == 'BUY' else entry_price + (atr * 2)
                    tp = entry_price + (atr * 5) if signal == 'BUY' else entry_price - (atr * 5)
                    
                    open_trade = {
                        'time': current_time,
                        'type': signal,
                        'entry': entry_price,
                        'sl': sl,
                        'tp': tp,
                        'risk_dollars': risk_dollars,
                        'tp_multiplier': tp_multiplier
                    }

        # 3. Print Results
        df_trades = pd.DataFrame(trades)
        if df_trades.empty:
            print(f"📭 No trades executed for {symbol} in the backtest period.")
            return None

        total_profit = df_trades['pnl'].sum()
        win_rate = (df_trades['pnl'] > 0).mean() * 100
        max_dd = self.calculate_max_drawdown(self.equity_curve)
        
        print("\n" + "="*40)
        print(f"📊 BACKTEST RESULTS: {symbol}")
        print("="*40)
        print(f"Period:       {days} Days")
        print(f"Total Trades: {len(df_trades)}")
        print(f"Win Rate:     {win_rate:.2f}%")
        print(f"Total PnL:    ${total_profit:,.2f}")
        print(f"Max Drawdown: {max_dd:.2f}%")
        print(f"End Balance:  ${balance:,.2f}")
        print("="*40)

        return trades

    def calculate_max_drawdown(self, equity_curve):
        if not equity_curve: return 0
        peak = equity_curve[0]
        max_dd = 0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = ((peak - val) / peak) * 100
            if dd > max_dd:
                max_dd = dd
        return max_dd
