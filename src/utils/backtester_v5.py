import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from src.strategies.institutional_v5 import InstitutionalStrategyV5
from src.utils.market_math import calculate_atr, calculate_rsi, calculate_vwap
import matplotlib.pyplot as plt

class BacktesterV5:
    """
    High-Fidelity Backtester for V5 Institutional Strategy.
    Simulates execution over historical MT5 data and records deep snapshots for AI learning.
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
        self.trade_snapshots = [] # New: Store deep data for AI learning

    def _convert_to_datetime(self, t):
        """Helper to ensure we have a displayable datetime-like object."""
        if isinstance(t, (int, float, np.int64)):
            return datetime.fromtimestamp(t)
        return t # Assume pandas Timestamp or datetime

    def _capture_snapshot(self, symbol, current_time, mtf_data, signal, reason):
        """
        Captures the state of the market indicators at the moment of entry.
        """
        try:
            m15 = mtf_data['M15']
            h1 = mtf_data['H1']
            h4 = mtf_data['H4']
            
            # Extract basic indicator values
            rsi = calculate_rsi(m15) # Already returns scalar .iloc[-1]
            atr = calculate_atr(m15) # Already returns scalar .iloc[-1]
            vwap_series = calculate_vwap(m15)
            vwap = vwap_series.iloc[-1]
            last_close = m15['close'].iloc[-1]
            dist_from_vwap = last_close - vwap
            
            # Trend context
            h1_ma = h1['close'].rolling(50).mean().iloc[-1]
            h4_ma = h4['close'].rolling(50).mean().iloc[-1]
            
            snapshot = {
                'symbol': symbol,
                'time': str(self._convert_to_datetime(current_time)),
                'signal': signal,
                'reason': reason,
                'indicators': {
                    'rsi_m15': float(rsi),
                    'atr_m15': float(atr),
                    'vwap_dist': float(dist_from_vwap),
                    'h1_trend_aligned': bool((signal == 'BUY' and last_close > h1_ma) or (signal == 'SELL' and last_close < h1_ma)),
                    'h4_trend_aligned': bool((signal == 'BUY' and last_close > h4_ma) or (signal == 'SELL' and last_close < h4_ma)),
                    'volume_z_score': float((m15['tick_volume'].iloc[-1] - m15['tick_volume'].tail(20).mean()) / m15['tick_volume'].tail(20).std())
                }
            }
            return snapshot
        except Exception as e:
            print(f"⚠️ Snapshot capture failed: {e}")
            return None

    def run(self, symbol, days=365):
        """
        Runs the backtest for a specific symbol.
        """
        print(f"\n⌛ Starting {days}-Day ({round(days/365, 1)}y) Backtest for {symbol}...")
        print(f"💰 Initial Balance: ${self.initial_balance:,.2f}")
        
        # 1. Fetch Data
        print("📥 Fetching historical data...")
        h4_bars = days * 6 + 200
        h1_bars = days * 24 + 300
        m15_bars = days * 96 + 500
        m5_bars = days * 288 + 1000

        data_h4 = self.bridge.get_data(symbol, mt5.TIMEFRAME_H4, h4_bars)
        data_h1 = self.bridge.get_data(symbol, mt5.TIMEFRAME_H1, h1_bars)
        data_m15 = self.bridge.get_data(symbol, mt5.TIMEFRAME_M15, m15_bars)
        data_m5 = self.bridge.get_data(symbol, mt5.TIMEFRAME_M5, m5_bars)

        if len(data_h4) < 100 or len(data_m15) < 300:
            print(f"❌ Insufficient data for {symbol}.")
            return None

        latest_start = max(data_h4['time'].iloc[0], data_h1['time'].iloc[0], data_m15['time'].iloc[0], data_m5['time'].iloc[0])
        data_m15 = data_m15[data_m15['time'] >= latest_start].reset_index(drop=True)

        strategy = InstitutionalStrategyV5(symbol, self.config)
        balance = self.initial_balance
        self.equity_curve = [balance]
        
        open_trade = None
        current_snapshot = None

        total_steps = len(data_m15)
        print("⚙️ Simulating...")
        
        for i in range(200, total_steps):
            current_time = data_m15['time'].iloc[i]
            
            mtf_data = {
                'H4': data_h4[data_h4['time'] <= current_time].tail(100),
                'H1': data_h1[data_h1['time'] <= current_time].tail(200),
                'M15': data_m15[data_m15['time'] <= current_time].tail(300),
                'M5': data_m5[data_m5['time'] <= current_time].tail(500)
            }

            # --- Check Exit ---
            if open_trade:
                row = data_m15.iloc[i]
                is_buy = open_trade['type'] == 'BUY'
                hit_sl = (is_buy and row['low'] <= open_trade['sl']) or (not is_buy and row['high'] >= open_trade['sl'])
                hit_tp = (is_buy and row['high'] >= open_trade['tp']) or (not is_buy and row['low'] <= open_trade['tp'])

                if hit_sl or hit_tp:
                    pnl = open_trade['risk_dollars'] * open_trade['tp_multiplier'] if hit_tp else -open_trade['risk_dollars']
                    balance += pnl
                    self.equity_curve.append(balance)
                    
                    # Link snapshot with result
                    if current_snapshot:
                        current_snapshot['outcome'] = {
                            'pnl': float(pnl),
                            'reason': 'TP' if hit_tp else 'SL',
                            'duration_minutes': int((current_time - open_trade['time']).total_seconds() / 60) if isinstance(current_time, pd.Timestamp) else 0
                        }
                        self.trade_snapshots.append(current_snapshot)
                        current_snapshot = None

                    open_trade = None

            # --- Check Entry ---
            if not open_trade:
                signal, reason = strategy.check_signal(mtf_data, sentiment_boost=0, regime='TRENDING') 
                if signal:
                    entry_price = data_m15['close'].iloc[i]
                    atr = calculate_atr(mtf_data['M15'])
                    risk_percent = self.config['risk_management'].get('max_risk_per_trade_percent', 1.0) / 100.0
                    risk_dollars = balance * risk_percent
                    tp_multiplier = 2.5
                    sl = entry_price - (atr * 2) if signal == 'BUY' else entry_price + (atr * 2)
                    tp = entry_price + (atr * 5) if signal == 'BUY' else entry_price - (atr * 5)
                    
                    open_trade = {'time': current_time, 'type': signal, 'entry': entry_price, 'sl': sl, 'tp': tp, 'risk_dollars': risk_dollars, 'tp_multiplier': tp_multiplier}
                    
                    # Capture deep snapshot for AI learning
                    current_snapshot = self._capture_snapshot(symbol, current_time, mtf_data, signal, reason)

        # Final Results log
        self._save_learning_data()
        
        df_trades = pd.DataFrame([s['outcome'] for s in self.trade_snapshots if 'outcome' in s])
        if df_trades.empty:
            print(f"📭 No trades executed for {symbol}.")
            return None

        total_profit = df_trades['pnl'].sum()
        win_rate = (df_trades['pnl'] > 0).mean() * 100
        max_dd = self.calculate_max_drawdown(self.equity_curve)
        
        print(f"\n📊 RESULTS: {symbol} | Trades: {len(df_trades)} | Win Rate: {win_rate:.1f}% | PnL: ${total_profit:,.2f} | MaxDD: {max_dd:.1f}%")
        return self.trade_snapshots

    def _save_learning_data(self):
        """Saves captured trade snapshots to a JSON file for AI analysis."""
        os.makedirs("logs", exist_ok=True)
        log_path = os.path.join("logs", "backtest_learning_data.json")
        try:
            with open(log_path, 'w') as f:
                json.dump(self.trade_snapshots, f, indent=4)
            print(f"📝 Deep learning data saved to {log_path} ({len(self.trade_snapshots)} records)")
        except Exception as e:
            print(f"❌ Failed to save learning data: {e}")

    def calculate_max_drawdown(self, equity_curve):
        if not equity_curve: return 0
        peak = equity_curve[0]
        max_dd = 0
        for val in equity_curve:
            if val > peak: peak = val
            dd = ((peak - val) / peak) * 100
            if dd > max_dd: max_dd = dd
        return max_dd
