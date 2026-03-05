"""
Trade Database - SQLite storage for all trade data
Replaces lessons_learned.json with proper statistical tracking
"""
import sqlite3
import time
from datetime import datetime

import os

class TradeDB:
    def __init__(self, db_path=None):
        if db_path is None:
            # Set default path relative to project root
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(root_dir, 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            self.db_path = os.path.join(data_dir, 'trades.db')
        else:
            self.db_path = db_path
        self.init_database()

    
    def init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER UNIQUE,
                timestamp REAL,
                symbol TEXT,
                direction TEXT,
                entry_price REAL,
                exit_price REAL,
                sl REAL,
                tp REAL,
                lot_size REAL,
                pnl REAL,
                r_multiple REAL,
                regime TEXT,
                atr REAL,
                spread REAL,
                slippage REAL,
                strategy TEXT,
                exit_reason TEXT,
                duration_seconds REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_trade_entry(self, ticket, symbol, direction, entry_price, sl, tp, lot_size, regime, atr, strategy):
        """Log trade entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trades (ticket, timestamp, symbol, direction, entry_price, sl, tp, lot_size, regime, atr, strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ticket, time.time(), symbol, direction, entry_price, sl, tp, lot_size, regime, atr, strategy))
        
        conn.commit()
        conn.close()
    
    def log_trade_exit(self, ticket, exit_price, pnl, exit_reason):
        """Update trade with exit data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get entry data to calculate R-multiple and duration
        cursor.execute('SELECT timestamp, entry_price, sl FROM trades WHERE ticket = ?', (ticket,))
        row = cursor.fetchone()
        
        if row:
            entry_time, entry_price, sl = row
            duration = time.time() - entry_time
            
            # Calculate R-multiple
            risk = abs(entry_price - sl)
            if risk > 0:
                r_multiple = pnl / risk if pnl != 0 else 0
            else:
                r_multiple = 0
            
            cursor.execute('''
                UPDATE trades 
                SET exit_price = ?, pnl = ?, r_multiple = ?, exit_reason = ?, duration_seconds = ?
                WHERE ticket = ?
            ''', (exit_price, pnl, r_multiple, exit_reason, duration, ticket))
        
        conn.commit()
        conn.close()
    
    def get_stats_last_n_trades(self, n=100):
        """Get statistics for last N trades"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                AVG(pnl) as avg_pnl,
                AVG(r_multiple) as avg_r,
                SUM(pnl) as total_pnl
            FROM trades 
            WHERE pnl IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (n,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] > 0:
            total, wins, losses, avg_pnl, avg_r, total_pnl = row
            win_rate = (wins / total * 100) if total > 0 else 0
            
            return {
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_pnl': avg_pnl,
                'avg_r': avg_r,
                'total_pnl': total_pnl
            }
        
        return None
    
    def get_expectancy(self):
        """Calculate expectancy (avg win * win_rate - avg_loss * loss_rate)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN ABS(pnl) END) as avg_loss,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate
            FROM trades
            WHERE pnl IS NOT NULL
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] and row[1]:
            avg_win, avg_loss, win_rate = row
            expectancy = (avg_win * win_rate) - (avg_loss * (1 - win_rate))
            return expectancy
        
        return None
