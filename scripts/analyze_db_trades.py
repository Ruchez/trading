import sqlite3
import pandas as pd
import os

def analyze_db():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(root_dir, 'data', 'trades.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    
    # Query all trades
    query = "SELECT * FROM trades ORDER BY timestamp DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print("No trades found in the local database.")
        return

    # Convert timestamp
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    print("\n--- Local Bot Trade Database Analysis ---")
    cols_to_show = ['ticket', 'datetime', 'symbol', 'direction', 'lot_size', 'pnl', 'strategy', 'regime']
    print(df[cols_to_show].head(20).to_string(index=False))
    
    print(f"\nTotal Bot Trades logged: {len(df)}")
    if 'pnl' in df.columns:
        print(f"Bot Total PnL: {round(df['pnl'].dropna().sum(), 2)}")
        win_rate = (len(df[df['pnl'] > 0]) / len(df[df['pnl'] != 0])) * 100 if len(df[df['pnl'] != 0]) > 0 else 0
        print(f"Bot Win Rate: {round(win_rate, 2)}%")

if __name__ == "__main__":
    analyze_db()
