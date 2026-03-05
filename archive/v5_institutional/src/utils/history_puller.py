import MetaTrader5 as mt5
import pandas as pd
import json
import os
from datetime import datetime, timedelta

def load_credentials():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config', 'accounts.json')
    try:
        with open(config_path, 'r') as f:
            accounts = json.load(f)
            # Find the first account with valid login
            for acc in accounts:
                if acc.get('login') and acc.get('login') != 0:
                    return acc
    except Exception as e:
        print(f"Error loading credentials: {e}")
    return None

def pull_mt5_history(days=30):
    acc = load_credentials()
    if not acc:
        print("No valid credentials found in config/accounts.json")
        return None

    if not mt5.initialize():
        print(f"MT5 initialize failed, error code: {mt5.last_error()}")
        return None

    authorized = mt5.login(
        login=int(acc['login']),
        password=acc['password'],
        server=acc['server']
    )

    if not authorized:
        print(f"Failed to connect to account {acc['login']}, error code: {mt5.last_error()}")
        mt5.shutdown()
        return None

    print(f"Connected to {acc['server']} (Account: {acc['login']})")

    # Define time range
    from_date = datetime.now() - timedelta(days=days)
    to_date = datetime.now()

    # Get history deals
    deals = mt5.history_deals_get(from_date, to_date)
    if deals is None:
        print(f"No deals found or error: {mt5.last_error()}")
        mt5.shutdown()
        return None

    if len(deals) == 0:
        print("No historical deals found in the specified range.")
        mt5.shutdown()
        return None

    # Convert to DataFrame
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Filter for trade deals (entry/exit)
    # Entry: DEAL_ENTRY_IN, Exit: DEAL_ENTRY_OUT
    # Types: DEAL_TYPE_BUY, DEAL_TYPE_SELL
    
    print(f"Retrieved {len(df)} deals.")
    
    # Simple summary of positions
    # We'll group by position_id to get a per-trade view
    positions = []
    
    for pos_id, group in df.groupby('position_id'):
        if pos_id == 0: continue # Skip balance operations
        
        symbol = group['symbol'].iloc[0]
        total_pnl = group['profit'].sum() + group['commission'].sum() + group['swap'].sum()
        lot_size = group[group['entry'] == mt5.DEAL_ENTRY_IN]['volume'].sum()
        
        entry_time = group[group['entry'] == mt5.DEAL_ENTRY_IN]['time'].min()
        exit_time = group[group['entry'] == mt5.DEAL_ENTRY_OUT]['time'].max()
        
        positions.append({
            'position_id': pos_id,
            'symbol': symbol,
            'lot_size': lot_size,
            'pnl': round(total_pnl, 2),
            'entry_time': entry_time,
            'exit_time': exit_time,
            'type': 'BUY' if group[group['entry'] == mt5.DEAL_ENTRY_IN]['type'].iloc[0] == mt5.DEAL_TYPE_BUY else 'SELL'
        })

    pos_df = pd.DataFrame(positions)
    
    # Save to CSV
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    export_path = os.path.join(data_dir, 'history_export.csv')
    pos_df.to_csv(export_path, index=False)
    print(f"DONE: History exported to {export_path}")

    mt5.shutdown()
    return pos_df

if __name__ == "__main__":
    history = pull_mt5_history(days=90) # Default to 90 days
    if history is not None and not history.empty:
        print("\n--- Recent Trading History Summary ---")
        print(history.sort_values('exit_time', ascending=False).head(10).to_string(index=False))
        print(f"\nTotal Trades: {len(history)}")
        print(f"Total PnL: {round(history['pnl'].sum(), 2)}")
