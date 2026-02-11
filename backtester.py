import pandas as pd
import numpy as np
from datetime import datetime
import MetaTrader5 as mt5

class Backtester:
    """
    Simulation engine for institutional strategies.
    Replays history and calculates 'Potential PnL'.
    """
    def __init__(self, bridge, risk_engine, config):
        self.bridge = bridge
        self.risk_engine = risk_engine
        self.config = config
        self.trades = []
        self.equity_curve = [100.0] # Starting with 100 USD (user's balance)
        
    def download_history(self, symbol, timeframe, days=30):
        """
        Pulls clean historical data from MT5 for simulation.
        """
        print(f"Downloading {days} days of history for {symbol}...")
        bars = self.bridge.get_data(symbol, timeframe, n=days*24*60) # Approx bars
        return bars

    def run(self, symbol, strategy, data):
        """
        The Core Simulation: Feeds data bar-by-bar to the strategy.
        """
        print(f"Starting backtest for {symbol}...")
        
        # Window of data the strategy 'sees'
        window_size = 250 
        balance = 100.0
        active_trades = []
        
        for i in range(window_size, len(data)):
            # Current slice of history
            historical_slice = data.iloc[i-window_size:i]
            current_bar = data.iloc[i]
            
            # 1. Check for Signal
            signal = strategy.check_signal(historical_slice)
            
            # 2. Simulate Entry
            if signal in ['BUY', 'SELL'] and len(active_trades) < 2:
                lot = 0.01
                entry_price = current_bar['close']
                
                # Mock SL/TP (200/400 points as per bridge)
                # Note: In real backtest we verify if SL/TP was hit in later bars
                trade = {
                    'symbol': symbol,
                    'type': signal,
                    'entry_time': current_bar['time'],
                    'entry_price': entry_price,
                    'lot': lot,
                    'status': 'OPEN'
                }
                active_trades.append(trade)
                
            # 3. Simulate Exit (Simple Mean Reversion or TP/SL logic)
            # This is a simplified version; a pro backtester monitors every M1 candle for SL/TP hits
            for trade in active_trades[:]:
                if strategy.check_exit(None, historical_slice): # Simplified exit
                    profit = (current_bar['close'] - trade['entry_price']) * 100 # Approx for 0.01 lot
                    if trade['type'] == 'SELL': profit *= -1
                    
                    trade['status'] = 'CLOSED'
                    trade['exit_price'] = current_bar['close']
                    trade['profit'] = profit
                    self.trades.append(trade)
                    active_trades.remove(trade)
                    balance += profit
                    self.equity_curve.append(balance)

        return self.get_summary()

    def get_summary(self):
        df = pd.DataFrame(self.trades)
        if df.empty: return "No trades executed."
        
        total_profit = df['profit'].sum()
        win_rate = (len(df[df['profit'] > 0]) / len(df)) * 100
        
        return {
            'Total Profit': f"${total_profit:.2f}",
            'Win Rate': f"{win_rate:.1f}%",
            'Total Trades': len(df),
            'Final Equity': f"${self.equity_curve[-1]:.2f}"
        }
