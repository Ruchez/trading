import MetaTrader5 as mt5
from security_vault import SecurityVault
import time

def test_link():
    print("--- MT5 Connectivity Test ---")
    vault = SecurityVault()
    
    if not vault.validate():
        print("[FAIL] .env file is missing or MT5_LOGIN is not set.")
        return

    print(f"Attempting to connect to: {vault.server}...")
    
    creds = vault.get_credentials()
    print("Initializing MT5 terminal...")
    
    if not mt5.initialize():
        error = mt5.last_error()
        print(f"[FAIL] mt5.initialize() failed. Error: {error}")
        print("Check if MetaTrader 5 terminal is installed and open.")
        return

    print(f"Attempting to login to: {creds['server']}...")
    authorized = mt5.login(
        login=creds['login'], 
        password=creds['password'], 
        server=creds['server']
    )

    if not authorized:
        error = mt5.last_error()
        print(f"[FAIL] mt5.login() failed. Error: {error}")
        print("Check if credentials are 100% correct and the server is accessible.")
        return

    account_info = mt5.account_info()
    if account_info:
        print("[SUCCESS] Connected to MT5!")
        account_info = mt5.account_info()
        print("[SUCCESS] Connected to MT5!")
        print(f"Account: {account_info.login}")
        print(f"Broker: {account_info.company}")
        print(f"Balance: {account_info.balance} {account_info.currency}")
        
        # Test data steam
        print("Scanned symbols containing 'XAU' or 'Gold':")
        symbols = mt5.symbols_get()
        found = False
        for s in symbols:
            if "XAU" in s.name or "GOLD" in s.name.upper():
                print(f" - Found: {s.name}")
                found = True
        
        if not found:
            print(" - No Gold symbols found in Market Watch.")

        symbol = "XAUUSD.m"
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"Latest {symbol} Price -> Bid: {tick.bid} | Ask: {tick.ask}")
        else:
            print(f"[WARNING] Could not get tick data for {symbol}.")
            
    else:
        print(f"[FAIL] Login failed. Error code: {mt5.last_error()}")

    mt5.shutdown()

if __name__ == "__main__":
    test_link()
